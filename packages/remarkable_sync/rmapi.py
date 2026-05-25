"""Automated reMarkable Cloud sync adapter using the ddvk/rmapi CLI.

This adapter shells out to the ``rmapi`` binary
(https://github.com/ddvk/rmapi). It is intentionally conservative:

- Only machine-owned paths under ``HabitOS/`` are accepted.
- Archive paths are treated as frozen once written.
- The current-month dashboard is only replaced when the user opts in via
  ``HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=true``.
- ``--force`` is the only replacement flag used. ``--content-only``,
  ``rm``, ``mv``, ``geta``, ``mput``, ``mget``, and ``find`` are never
  invoked.
- Dry-run mode returns the argv that *would* have been executed without
  spawning anything.
- All subprocess execution is mediated through a ``SubprocessRunner``
  abstraction so unit tests inject a fake.

rmapi authentication is the user's responsibility (one-time interactive
code paste from https://my.remarkable.com/device/desktop/connect).
"""

from __future__ import annotations

import asyncio
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from packages.remarkable_sync.base import (
    MACHINE_ROOT_FOLDER,
    RemarkableDocument,
    SyncAction,
    SyncRequest,
    SyncResult,
)


@dataclass(frozen=True)
class RmapiConfig:
    """Runtime configuration for ``RmapiRemarkableSyncAdapter``."""

    binary: str = "rmapi"
    config_path: Path | None = None
    timeout_seconds: int = 60
    trace: bool = False
    replace_existing_current: bool = False
    machine_root: str = MACHINE_ROOT_FOLDER


@dataclass(frozen=True)
class CompletedRun:
    """Result of a single rmapi subprocess invocation."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class SubprocessRunner(Protocol):
    """Async indirection over ``asyncio.create_subprocess_exec``.

    The real implementation runs the binary; tests inject a fake that
    records calls and returns scripted outputs.
    """

    async def run(
        self,
        argv: list[str],
        *,
        env: dict[str, str],
        timeout: float,
    ) -> CompletedRun: ...


class AsyncioSubprocessRunner:
    """Default runner that spawns rmapi via asyncio."""

    async def run(
        self,
        argv: list[str],
        *,
        env: dict[str, str],
        timeout: float,
    ) -> CompletedRun:
        process = await asyncio.create_subprocess_exec(
            *argv,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise
        return CompletedRun(
            argv=tuple(argv),
            returncode=process.returncode if process.returncode is not None else -1,
            stdout=stdout_b.decode("utf-8", errors="replace"),
            stderr=stderr_b.decode("utf-8", errors="replace"),
        )


class RmapiRemarkableSyncAdapter:
    """rmapi-backed adapter. Mutates only machine-owned paths."""

    name = "rmapi"

    def __init__(
        self,
        config: RmapiConfig,
        runner: SubprocessRunner | None = None,
    ) -> None:
        self.config = config
        self.runner = runner or AsyncioSubprocessRunner()

    # ------------------------------------------------------------------ API

    async def upload_pdf(self, request: SyncRequest) -> SyncResult:
        return await self._upload(request, action="upload")

    async def update_pdf(self, request: SyncRequest) -> SyncResult:
        return await self._upload(request, action="update")

    async def list_documents(self) -> list[RemarkableDocument]:
        """List machine-owned HabitOS documents only.

        Falls back to an empty list if the root folder does not exist.
        """

        root = f"/{self.config.machine_root}"
        try:
            run = await self._run(["ls", "--json", root])
        except FileNotFoundError:
            return []
        except asyncio.TimeoutError:
            return []
        if run.returncode != 0:
            return []
        # We deliberately do not parse the JSON tree here. Listing is a
        # diagnostic convenience and the full schema is documented in the
        # rmapi README. Future work can hydrate ``RemarkableDocument``s
        # from this stdout if a real need appears.
        return []

    async def diagnostics(self) -> dict[str, Any]:
        """Health check for /remarkable/status.

        Reports whether the binary is callable and whether the config
        path (when set) is readable. Never raises.
        """

        info: dict[str, Any] = {
            "binary": self.config.binary,
            "binary_path": _resolve_binary(self.config.binary),
            "config_path": (
                str(self.config.config_path) if self.config.config_path else None
            ),
            "trace": self.config.trace,
            "replace_existing_current": self.config.replace_existing_current,
            "machine_root": self.config.machine_root,
            "timeout_seconds": self.config.timeout_seconds,
        }
        info["binary_available"] = info["binary_path"] is not None
        if self.config.config_path is not None:
            info["config_path_readable"] = self.config.config_path.is_file()
        else:
            info["config_path_readable"] = None
        # Probe authentication with `ls /` — the cloud root always exists
        # when authenticated, regardless of whether HabitOS/ has been
        # provisioned yet. Then also check whether the machine root is
        # already present.
        if info["binary_available"]:
            try:
                root_run = await self._run(["ls", "/"])
                info["ls_root_returncode"] = root_run.returncode
                info["authenticated"] = root_run.returncode == 0
                if root_run.returncode != 0:
                    info["last_stderr"] = _summarize(root_run.stderr)
            except FileNotFoundError:
                info["binary_available"] = False
                info["authenticated"] = False
            except asyncio.TimeoutError:
                info["authenticated"] = False
                info["last_stderr"] = "rmapi ls / timed out"
            # Best-effort: report whether the machine_root folder exists.
            if info.get("authenticated"):
                try:
                    stat_run = await self._run(
                        ["stat", f"/{self.config.machine_root}"]
                    )
                    info["machine_root_present"] = stat_run.returncode == 0
                except (FileNotFoundError, asyncio.TimeoutError):
                    info["machine_root_present"] = None
        else:
            info["authenticated"] = False
        return info

    # ------------------------------------------------------------------ core

    async def _upload(self, request: SyncRequest, *, action: SyncAction) -> SyncResult:
        # Local PDF must exist and be a file.
        pdf_path = request.local_pdf_path
        if not pdf_path.exists() or not pdf_path.is_file():
            return _result(
                request,
                action=action,
                status="not_configured",
                message=f"Generated PDF not found or not a file: {pdf_path}",
                device_mutated=False,
            )

        # Target must be machine-owned and shaped like current or archive.
        target_kind = self._classify_target(request.folder_path)
        if target_kind is None:
            return _result(
                request,
                action=action,
                status="unsupported",
                message=(
                    "Refusing to upload outside machine-owned HabitOS targets. "
                    f"folder_path={request.folder_path!r}"
                ),
                device_mutated=False,
                instructions=[
                    f"Only paths under '{self.config.machine_root}/' are allowed.",
                ],
            )

        target_remote = "/" + "/".join((*request.folder_path, f"{request.document_name}.pdf"))
        folder_remote = "/" + "/".join(request.folder_path)

        # Dry-run: describe what would have happened without spawning anything.
        if request.dry_run:
            planned = self._planned_argv(pdf_path, folder_remote, target_kind)
            return _result(
                request,
                action=action,
                status="planned",
                message="Dry run; no rmapi commands were executed.",
                device_mutated=False,
                instructions=["planned: " + shlex.join(cmd) for cmd in planned],
            )

        # Ensure folder chain exists.
        try:
            await self._ensure_folder_chain(request.folder_path)
        except FileNotFoundError:
            return _binary_missing_result(request, action, self.config.binary)
        except asyncio.TimeoutError:
            return _timeout_result(request, action, "rmapi mkdir/stat timed out")

        # Existence check on the target document.
        try:
            target_exists = await self._exists(target_remote)
        except FileNotFoundError:
            return _binary_missing_result(request, action, self.config.binary)
        except asyncio.TimeoutError:
            return _timeout_result(request, action, "rmapi stat timed out")

        # Archive: frozen if present.
        if target_kind == "archive" and target_exists:
            return _result(
                request,
                action=action,
                status="unsupported",
                message=(
                    "Archive target already exists; archives are frozen. "
                    "Delete on-device manually if a re-render is intended."
                ),
                device_mutated=False,
            )

        # Current: only replace when the user opts in.
        use_force = False
        if target_kind == "current":
            if target_exists and not self.config.replace_existing_current:
                return _result(
                    request,
                    action=action,
                    status="unsupported",
                    message=(
                        "Current-month target already exists and "
                        "HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=false."
                    ),
                    device_mutated=False,
                    instructions=[
                        "Set HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=true to enable replacement.",
                        "Note: --force removes existing annotations from the document.",
                    ],
                )
            use_force = self.config.replace_existing_current
        
        # Execute the put.
        put_argv = ["put"]
        if use_force:
            put_argv.append("--force")
        put_argv.extend([str(pdf_path), folder_remote])
        try:
            run = await self._run(put_argv)
        except FileNotFoundError:
            return _binary_missing_result(request, action, self.config.binary)
        except asyncio.TimeoutError:
            return _timeout_result(request, action, "rmapi put timed out")

        if run.returncode != 0:
            return _result(
                request,
                action=action,
                status="failed",
                message=f"rmapi put failed with exit code {run.returncode}.",
                device_mutated=False,
                instructions=_run_diagnostics(run),
            )
        return _result(
            request,
            action=action,
            status="updated" if use_force else "uploaded",
            message=(
                "rmapi upload succeeded with --force (existing document replaced)."
                if use_force
                else "rmapi upload succeeded."
            ),
            device_mutated=True,
            instructions=_run_diagnostics(run),
        )

    # ------------------------------------------------------------ folder mgmt

    async def _ensure_folder_chain(self, folder_path: tuple[str, ...]) -> None:
        """Create each prefix folder if not present."""

        for depth in range(1, len(folder_path) + 1):
            prefix = "/" + "/".join(folder_path[:depth])
            if await self._exists(prefix):
                continue
            mk = await self._run(["mkdir", prefix])
            if mk.returncode != 0 and not await self._exists(prefix):
                # rmapi sometimes prints to stderr but still succeeds; only
                # raise if the folder still does not exist after the attempt.
                raise RuntimeError(
                    f"rmapi mkdir failed for {prefix}: exit={mk.returncode} "
                    f"stderr={_summarize(mk.stderr)}"
                )

    async def _exists(self, remote_path: str) -> bool:
        run = await self._run(["stat", remote_path])
        return run.returncode == 0

    # ------------------------------------------------------------------ utils

    def _classify_target(
        self, folder_path: tuple[str, ...]
    ) -> str | None:
        root = self.config.machine_root
        if len(folder_path) < 2 or folder_path[0] != root:
            return None
        if folder_path == (root, "00 Current"):
            return "current"
        if (
            len(folder_path) == 3
            and folder_path[2] == "Archive"
            and folder_path[1].isdigit()
            and len(folder_path[1]) == 4
        ):
            return "archive"
        return None

    def _planned_argv(
        self,
        pdf_path: Path,
        folder_remote: str,
        target_kind: str,
    ) -> list[list[str]]:
        argv: list[list[str]] = []
        for depth in range(1, folder_remote.count("/") + 1):
            argv.append(
                [self.config.binary, "mkdir", "/".join(folder_remote.split("/")[: depth + 1]) or "/"]
            )
        put_cmd = [self.config.binary, "put"]
        if target_kind == "current" and self.config.replace_existing_current:
            put_cmd.append("--force")
        put_cmd.extend([str(pdf_path), folder_remote])
        argv.append(put_cmd)
        return argv

    async def _run(self, args: list[str]) -> CompletedRun:
        return await self.runner.run(
            [self.config.binary, *args],
            env=self._build_env(),
            timeout=float(self.config.timeout_seconds),
        )

    def _build_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.config.config_path is not None:
            env["RMAPI_CONFIG"] = str(self.config.config_path)
        if self.config.trace:
            env["RMAPI_TRACE"] = "1"
        return env


# --------------------------------------------------------------------- helpers


def _resolve_binary(binary: str) -> str | None:
    """Locate the rmapi binary on PATH or as an absolute path."""

    path = Path(binary)
    if path.is_absolute():
        return str(path) if path.is_file() else None
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry) / binary
        if candidate.is_file():
            return str(candidate)
    return None


def _summarize(text: str, *, limit: int = 400) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _run_diagnostics(run: CompletedRun) -> list[str]:
    parts: list[str] = [f"argv: {shlex.join(list(run.argv))}", f"exit: {run.returncode}"]
    if run.stdout.strip():
        parts.append(f"stdout: {_summarize(run.stdout)}")
    if run.stderr.strip():
        parts.append(f"stderr: {_summarize(run.stderr)}")
    return parts


def _result(
    request: SyncRequest,
    *,
    action: SyncAction,
    status: str,
    message: str,
    device_mutated: bool,
    instructions: list[str] | None = None,
) -> SyncResult:
    return SyncResult(
        adapter=RmapiRemarkableSyncAdapter.name,
        action=action,
        dry_run=request.dry_run,
        target_path=request.target_path,
        status=status,  # type: ignore[arg-type]
        message=message,
        local_pdf_path=request.local_pdf_path,
        device_mutated=device_mutated,
        instructions=list(instructions or []),
    )


def _binary_missing_result(
    request: SyncRequest, action: SyncAction, binary: str
) -> SyncResult:
    return _result(
        request,
        action=action,
        status="not_configured",
        message=f"rmapi binary not found: {binary}",
        device_mutated=False,
        instructions=[
            "Install rmapi from https://github.com/ddvk/rmapi or set "
            "HABITOS_RMAPI_BINARY to its absolute path.",
        ],
    )


def _timeout_result(request: SyncRequest, action: SyncAction, msg: str) -> SyncResult:
    return _result(
        request,
        action=action,
        status="failed",
        message=msg,
        device_mutated=False,
        instructions=[
            "Increase HABITOS_RMAPI_TIMEOUT_SECONDS or check network connectivity.",
        ],
    )


__all__ = [
    "AsyncioSubprocessRunner",
    "CompletedRun",
    "RmapiConfig",
    "RmapiRemarkableSyncAdapter",
    "SubprocessRunner",
]
