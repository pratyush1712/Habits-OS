"""Automated reMarkable Cloud sync adapter using the ddvk/rmapi CLI.

This adapter shells out to the ``rmapi`` binary
(https://github.com/ddvk/rmapi). It is intentionally conservative:

- Only machine-owned paths under ``HabitOS/`` (archives) or the fixed home-screen
  document name are accepted.
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
import logging
import os
import re
import shlex
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

from packages.remarkable_sync.rmdoc import (
    MalformedBundle,
    PageCountMismatch,
    copy_with_visible_name,
    swap_base_pdf,
)
from packages.remarkable_sync.base import (
    CURRENT_DOCUMENT_NAME,
    MACHINE_ROOT_FOLDER,
    RemarkableDocument,
    SyncAction,
    SyncRequest,
    SyncResult,
)

_LS_LINE_RE = re.compile(r"^\[([fd])\]\t(.+)$")


@dataclass(frozen=True)
class RmapiConfig:
    """Runtime configuration for ``RmapiRemarkableSyncAdapter``."""

    binary: str = "rmapi"
    config_path: Path | None = None
    timeout_seconds: int = 60
    trace: bool = False
    replace_existing_current: bool = False
    preserve_annotations: bool = True
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
        cwd: str | None = None,
    ) -> CompletedRun: ...


class AsyncioSubprocessRunner:
    """Default runner that spawns rmapi via asyncio."""

    async def run(
        self,
        argv: list[str],
        *,
        env: dict[str, str],
        timeout: float,
        cwd: str | None = None,
    ) -> CompletedRun:
        process = await asyncio.create_subprocess_exec(
            *argv,
            env=env,
            cwd=cwd,
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

    async def archive_device_document(
        self,
        source_document_name: str,
        target_folder_path: tuple[str, ...],
        target_document_name: str,
        dry_run: bool = False,
    ) -> SyncResult:
        """Snapshot an existing on-device document into the frozen archive folder.

        Downloads the home-screen document as an ``.rmdoc`` (which carries every
        ``.rm`` annotation blob), rewrites its display name to the archive name,
        and uploads it under ``HabitOS/<year>/Archive/``. This is what preserves
        the user's handwriting when a month rolls over, instead of uploading a
        fresh annotation-free PDF.

        Archives are frozen: if the target already exists this is a no-op, so the
        operation is safe to run more than once (e.g. a startup catch-up run plus
        the nightly cron both firing on the 1st).
        """

        request = SyncRequest(
            local_pdf_path=Path(),
            document_name=target_document_name,
            folder_path=target_folder_path,
            dry_run=dry_run,
        )

        if dry_run:
            return _result(
                request,
                action="upload",
                status="planned",
                message="Dry run; archive the on-device document with all annotations preserved.",
                device_mutated=False,
                instructions=[
                    f"planned: rmapi ls {self._remote_folder_path(target_folder_path)} "
                    f"→ skip if '{target_document_name}' already archived",
                    f"planned: rmapi ls / → resolve '{source_document_name}' exact name",
                    "planned: rmapi get '/<resolved-name>' → download .rmdoc (with ink)",
                    f"planned: rewrite bundle visibleName to '{target_document_name}'",
                    f"planned: rmapi mkdir {self._remote_folder_path(target_folder_path)}",
                    f"planned: rmapi put '<tmp>/{target_document_name}.rmdoc' "
                    f"{self._remote_folder_path(target_folder_path)}",
                ],
            )

        tmp = Path(tempfile.mkdtemp(prefix="habitos-rmapi-"))
        try:
            # Archives are frozen — never overwrite an existing snapshot.
            try:
                if await self._document_exists_in_folder(
                    target_folder_path, target_document_name
                ):
                    return _result(
                        request,
                        action="upload",
                        status="uploaded",
                        message=(
                            f"Archive '{target_document_name}' already exists; left "
                            "untouched (archives are frozen)."
                        ),
                        device_mutated=False,
                    )
            except FileNotFoundError:
                return _binary_missing_result(request, "upload", self.config.binary)
            except asyncio.TimeoutError:
                return _timeout_result(request, "upload", "rmapi ls timed out")

            # Resolve the actual on-device name (may carry a month label).
            try:
                resolved_name = await self._resolve_current_doc_name()
            except FileNotFoundError:
                return _binary_missing_result(request, "upload", self.config.binary)
            except asyncio.TimeoutError:
                return _timeout_result(
                    request, "upload", "rmapi ls / timed out while resolving document name"
                )
            except _LsFailed as e:
                return _result(
                    request,
                    action="upload",
                    status="failed",
                    message=f"rmapi ls / failed with exit code {e.run.returncode}.",
                    device_mutated=False,
                    instructions=_run_diagnostics(e.run),
                )
            except _AmbiguousCurrentDoc as e:
                return _result(
                    request,
                    action="upload",
                    status="unsupported",
                    message=(
                        "Multiple home-screen documents match the current-month "
                        f"name '{source_document_name}'; refusing to guess which to archive."
                    ),
                    device_mutated=False,
                    instructions=[
                        f"candidates: {', '.join(e.candidates)}",
                        "Rename or remove the extras so exactly one matches.",
                    ],
                )

            if resolved_name is None:
                return _result(
                    request,
                    action="upload",
                    status="failed",
                    message=f"Current-month document '{source_document_name}' not found on device.",
                    device_mutated=False,
                    instructions=[
                        f"Make sure a document named '{source_document_name}' exists "
                        "on the device home screen before archiving.",
                    ],
                )

            # Download the .rmdoc bundle (with all .rm annotation blobs).
            dl = tmp / "dl"
            dl.mkdir()
            try:
                run = await self._run(["get", f"/{resolved_name}"], cwd=str(dl))
            except FileNotFoundError:
                return _binary_missing_result(request, "upload", self.config.binary)
            except asyncio.TimeoutError:
                return _timeout_result(
                    request, "upload", "rmapi get timed out while downloading the document"
                )
            if run.returncode != 0:
                return _result(
                    request,
                    action="upload",
                    status="failed",
                    message=f"rmapi get failed with exit code {run.returncode}.",
                    device_mutated=False,
                    instructions=_run_diagnostics(run),
                )

            downloaded = dl / f"{resolved_name}.rmdoc"
            if not downloaded.is_file():
                found = list(dl.glob("*.rmdoc"))
                if not found:
                    return _result(
                        request,
                        action="upload",
                        status="failed",
                        message="rmapi get did not produce an .rmdoc bundle.",
                        device_mutated=False,
                        instructions=_run_diagnostics(run),
                    )
                downloaded = found[0]

            # Rewrite the display name so the archive entry reads e.g.
            # "2026-05 Habit Dashboard" rather than inheriting "01. Habit Tracker".
            up = tmp / "up"
            up.mkdir()
            staged = up / f"{target_document_name}.rmdoc"
            try:
                copy_with_visible_name(downloaded, staged, target_document_name)
            except (MalformedBundle, KeyError) as e:
                return _result(
                    request,
                    action="upload",
                    status="failed",
                    message=f"Could not rewrite reMarkable bundle for archive: {e}",
                    device_mutated=False,
                )

            # Ensure the archive folder chain exists, then upload.
            try:
                await self._ensure_folder_chain(target_folder_path)
            except FileNotFoundError:
                return _binary_missing_result(request, "upload", self.config.binary)
            except asyncio.TimeoutError:
                return _timeout_result(
                    request, "upload", "rmapi mkdir timed out while creating the archive folder"
                )

            folder_remote = self._remote_folder_path(target_folder_path)
            try:
                run = await self._run(["put", str(staged), folder_remote])
            except FileNotFoundError:
                return _binary_missing_result(request, "upload", self.config.binary)
            except asyncio.TimeoutError:
                return _timeout_result(
                    request, "upload", "rmapi put timed out while uploading the archive"
                )
            if run.returncode != 0:
                return _result(
                    request,
                    action="upload",
                    status="failed",
                    message=f"rmapi put failed with exit code {run.returncode}.",
                    device_mutated=False,
                    instructions=_run_diagnostics(run),
                )

            return _result(
                request,
                action="upload",
                status="uploaded",
                message=(
                    f"Archived '{resolved_name}' as '{target_document_name}' "
                    "with all annotations preserved."
                ),
                device_mutated=True,
                instructions=_run_diagnostics(run),
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

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
            "preserve_annotations": self.config.preserve_annotations,
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
        target_kind = self._classify_target(
            request.folder_path,
            request.document_name,
        )
        if target_kind is None:
            return _result(
                request,
                action=action,
                status="unsupported",
                message=(
                    "Refusing to upload outside machine-owned HabitOS targets. "
                    f"folder_path={request.folder_path!r}, "
                    f"document_name={request.document_name!r}"
                ),
                device_mutated=False,
                instructions=[
                    f"Current month must be '{CURRENT_DOCUMENT_NAME}' on the device home screen.",
                    f"Archives must live under '{self.config.machine_root}/YYYY/Archive/'.",
                ],
            )

        folder_remote = self._remote_folder_path(request.folder_path)

        # Dry-run: describe what would have happened without spawning anything.
        if request.dry_run:
            return _result(
                request,
                action=action,
                status="planned",
                message="Dry run; no rmapi commands were executed.",
                device_mutated=False,
                instructions=self._planned_steps(request, target_kind, folder_remote),
            )

        if target_kind == "current":
            return await self._upload_current(request, action=action)
        return await self._upload_archive(
            request, action=action, folder_remote=folder_remote
        )

    # ------------------------------------------------------------ archive flow

    async def _upload_archive(
        self, request: SyncRequest, *, action: SyncAction, folder_remote: str
    ) -> SyncResult:
        target_remote = self._remote_document_path(
            request.folder_path, request.document_name
        )
        try:
            await self._ensure_folder_chain(request.folder_path)
        except FileNotFoundError:
            return _binary_missing_result(request, action, self.config.binary)
        except asyncio.TimeoutError:
            return _timeout_result(request, action, "rmapi mkdir/stat timed out")

        try:
            target_exists = await self._exists(target_remote)
        except FileNotFoundError:
            return _binary_missing_result(request, action, self.config.binary)
        except asyncio.TimeoutError:
            return _timeout_result(request, action, "rmapi stat timed out")

        if target_exists:
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

        try:
            run = await self._run(["put", str(request.local_pdf_path), folder_remote])
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
            status="uploaded",
            message="rmapi upload succeeded.",
            device_mutated=True,
            instructions=_run_diagnostics(run),
        )

    # ------------------------------------------------------------ current flow

    async def _upload_current(
        self, request: SyncRequest, *, action: SyncAction
    ) -> SyncResult:
        try:
            existing = await self._resolve_current_doc_name()
        except FileNotFoundError:
            return _binary_missing_result(request, action, self.config.binary)
        except asyncio.TimeoutError:
            return _timeout_result(request, action, "rmapi ls timed out")
        except _LsFailed as e:
            return _result(
                request,
                action=action,
                status="failed",
                message=f"rmapi ls / failed with exit code {e.run.returncode}.",
                device_mutated=False,
                instructions=_run_diagnostics(e.run),
            )
        except _AmbiguousCurrentDoc as e:
            return _result(
                request,
                action=action,
                status="unsupported",
                message=(
                    "Multiple home-screen documents match the current-month "
                    f"name '{CURRENT_DOCUMENT_NAME}'; refusing to guess which to update."
                ),
                device_mutated=False,
                instructions=[
                    f"candidates: {', '.join(e.candidates)}",
                    "Rename or remove the extras so exactly one matches.",
                ],
            )

        if existing is None:
            return await self._put_named(
                request,
                action,
                doc_name=CURRENT_DOCUMENT_NAME,
                force=False,
                status_ok="uploaded",
                message="rmapi upload succeeded (new current-month document created).",
            )

        # Month rollover: replace the home document with a fresh new-month page.
        # The prior month's ink has already been copied into the archive, and the
        # new month's page count differs, so a merge would wrongly abort. This is
        # independent of the preserve/replace config because the semantics here
        # are "start a clean month", not "refresh today's data".
        if request.reset:
            return await self._put_named(
                request,
                action,
                doc_name=existing,
                force=True,
                status_ok="updated",
                message=(
                    "rmapi reset succeeded (home document advanced to the new "
                    "month; previous month preserved in the archive)."
                ),
            )

        if self.config.replace_existing_current:
            return await self._put_named(
                request,
                action,
                doc_name=existing,
                force=True,
                status_ok="updated",
                message=(
                    "rmapi upload succeeded with --force "
                    "(existing document replaced; annotations dropped)."
                ),
            )

        if self.config.preserve_annotations:
            return await self._merge_current(request, action=action, doc_name=existing)

        return _result(
            request,
            action=action,
            status="unsupported",
            message=(
                f"Current-month document '{existing}' exists and both "
                "HABITOS_RMAPI_PRESERVE_ANNOTATIONS and "
                "HABITOS_RMAPI_REPLACE_EXISTING_CURRENT are false."
            ),
            device_mutated=False,
            instructions=[
                "Enable HABITOS_RMAPI_PRESERVE_ANNOTATIONS=true to refresh data while keeping ink.",
                "Or HABITOS_RMAPI_REPLACE_EXISTING_CURRENT=true to replace (drops ink).",
            ],
        )

    async def _put_named(
        self,
        request: SyncRequest,
        action: SyncAction,
        *,
        doc_name: str,
        force: bool,
        status_ok: str,
        message: str,
    ) -> SyncResult:
        """Put the rendered PDF under an explicit document name on the home screen.

        rmapi derives the cloud document name from the uploaded file's stem, so
        we stage the PDF under ``<doc_name>.pdf`` before putting it.
        """

        tmp = Path(tempfile.mkdtemp(prefix="habitos-rmapi-"))
        try:
            staged = tmp / f"{doc_name}.pdf"
            shutil.copyfile(request.local_pdf_path, staged)
            argv = ["put"]
            if force:
                argv.append("--force")
            argv.extend([str(staged), "/"])
            try:
                run = await self._run(argv)
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
                status=status_ok,
                message=message,
                device_mutated=True,
                instructions=_run_diagnostics(run),
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    async def _merge_current(
        self, request: SyncRequest, *, action: SyncAction, doc_name: str
    ) -> SyncResult:
        """Refresh the current-month data layer while keeping annotations.

        Downloads the existing ``.rmdoc``, swaps only its base PDF for the freshly
        rendered one (keeping ``.content`` page UUIDs and every ``.rm`` ink blob),
        and re-uploads. Aborts without mutating the device if the rendered PDF's
        page count differs from what is on the device.
        """

        tmp = Path(tempfile.mkdtemp(prefix="habitos-rmapi-"))
        dl = tmp / "dl"
        up = tmp / "up"
        dl.mkdir()
        up.mkdir()
        try:
            try:
                run = await self._run(["get", f"/{doc_name}"], cwd=str(dl))
            except FileNotFoundError:
                return _binary_missing_result(request, action, self.config.binary)
            except asyncio.TimeoutError:
                return _timeout_result(request, action, "rmapi get timed out")
            if run.returncode != 0:
                return _result(
                    request,
                    action=action,
                    status="failed",
                    message=f"rmapi get failed with exit code {run.returncode}.",
                    device_mutated=False,
                    instructions=_run_diagnostics(run),
                )

            downloaded = dl / f"{doc_name}.rmdoc"
            if not downloaded.is_file():
                found = list(dl.glob("*.rmdoc"))
                if not found:
                    return _result(
                        request,
                        action=action,
                        status="failed",
                        message="rmapi get did not produce an .rmdoc bundle.",
                        device_mutated=False,
                        instructions=_run_diagnostics(run),
                    )
                downloaded = found[0]

            merged = up / f"{doc_name}.rmdoc"
            try:
                info = swap_base_pdf(downloaded, request.local_pdf_path, merged)
            except PageCountMismatch as e:
                # Page count changed (e.g. month has fewer days than the previous
                # one).  Annotations would be misaligned regardless, so fall back
                # to a force-replace rather than blocking the upload entirely.
                logger.info(
                    "Page count changed (%s); falling back to force-replace.", e
                )
                return await self._put_named(
                    request,
                    action,
                    doc_name=doc_name,
                    force=True,
                    status_ok="updated",
                    message=(
                        "Page count changed (month length differs); "
                        "replaced document with fresh PDF (annotations dropped)."
                    ),
                )
            except (MalformedBundle, KeyError) as e:
                return _result(
                    request,
                    action=action,
                    status="failed",
                    message=f"Could not rewrite reMarkable bundle: {e}",
                    device_mutated=False,
                )

            try:
                run = await self._run(["put", "--force", str(merged), "/"])
            except FileNotFoundError:
                return _binary_missing_result(request, action, self.config.binary)
            except asyncio.TimeoutError:
                return _timeout_result(request, action, "rmapi put timed out")
            if run.returncode != 0:
                return _result(
                    request,
                    action=action,
                    status="failed",
                    message=f"rmapi merge put failed with exit code {run.returncode}.",
                    device_mutated=False,
                    instructions=_run_diagnostics(run),
                )
            return _result(
                request,
                action=action,
                status="updated",
                message=(
                    f"Refreshed '{doc_name}' data while preserving annotations "
                    f"({info.rm_file_count} ink file(s) kept across {info.page_count} pages)."
                ),
                device_mutated=True,
                instructions=_run_diagnostics(run),
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    async def _resolve_current_doc_name(self) -> str | None:
        """Return the home-screen document to treat as the current month, or None.

        Parses ``rmapi ls /`` and matches files named exactly
        ``CURRENT_DOCUMENT_NAME`` or prefixed by it (e.g. the month-labelled
        ``"01. Habit Tracker | May 2026"``). Raises on an ls failure or when more
        than one candidate is ambiguous, so we never overwrite the wrong document.
        """

        run = await self._run(["ls", "/"])
        if run.returncode != 0:
            raise _LsFailed(run)
        files = _parse_ls_files(run.stdout)
        candidates = [
            name
            for name in files
            if name == CURRENT_DOCUMENT_NAME
            or name.startswith(CURRENT_DOCUMENT_NAME + " ")
        ]
        if not candidates:
            return None
        if CURRENT_DOCUMENT_NAME in candidates:
            return CURRENT_DOCUMENT_NAME
        if len(candidates) == 1:
            return candidates[0]
        raise _AmbiguousCurrentDoc(candidates)

    def _planned_steps(
        self, request: SyncRequest, target_kind: str, folder_remote: str
    ) -> list[str]:
        if target_kind == "current":
            if request.reset:
                return [
                    "planned: rmapi ls /  (resolve the current-month document)",
                    "planned (rollover): rmapi put --force '<tmp>/<doc>.pdf' /  "
                    "(fresh new-month page; prior ink already archived)",
                ]
            return [
                "planned: rmapi ls /  (resolve the current-month document)",
                "planned (if absent): rmapi put "
                f"'<tmp>/{CURRENT_DOCUMENT_NAME}.pdf' /",
                "planned (if present, preserve on): rmapi get '/<doc>' "
                "→ swap base PDF, keep .content + .rm → rmapi put --force "
                "'<tmp>/<doc>.rmdoc' /",
                "planned (if present, replace on): rmapi put --force "
                "'<tmp>/<doc>.pdf' /  (drops annotations)",
            ]
        steps: list[str] = []
        for depth in range(1, len(request.folder_path) + 1):
            steps.append("planned: rmapi mkdir /" + "/".join(request.folder_path[:depth]))
        steps.append(f"planned: rmapi put '{request.local_pdf_path}' {folder_remote}")
        return steps

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

    async def _document_exists_in_folder(
        self, folder_path: tuple[str, ...], document_name: str
    ) -> bool:
        """True if a document named ``document_name`` lives directly in a folder.

        Matches on the visibleName as shown by ``rmapi ls`` (which is
        extension-less), so it is reliable regardless of how rmapi derives a
        document name from an uploaded file — unlike a ``stat`` on a
        ``.pdf``-suffixed path. A missing folder means the document cannot
        exist, so ``False``.
        """

        folder_remote = self._remote_folder_path(folder_path)
        run = await self._run(["ls", folder_remote])
        if run.returncode != 0:
            return False
        return document_name in _parse_ls_files(run.stdout)

    # ------------------------------------------------------------------ utils

    def _classify_target(
        self,
        folder_path: tuple[str, ...],
        document_name: str,
    ) -> str | None:
        if folder_path == () and document_name == CURRENT_DOCUMENT_NAME:
            return "current"

        root = self.config.machine_root
        if len(folder_path) < 2 or folder_path[0] != root:
            return None
        if (
            len(folder_path) == 3
            and folder_path[2] == "Archive"
            and folder_path[1].isdigit()
            and len(folder_path[1]) == 4
        ):
            return "archive"
        return None

    @staticmethod
    def _remote_folder_path(folder_path: tuple[str, ...]) -> str:
        if not folder_path:
            return "/"
        return "/" + "/".join(folder_path)

    @staticmethod
    def _remote_document_path(
        folder_path: tuple[str, ...],
        document_name: str,
    ) -> str:
        return "/" + "/".join((*folder_path, f"{document_name}.pdf"))

    async def _run(self, args: list[str], *, cwd: str | None = None) -> CompletedRun:
        return await self.runner.run(
            [self.config.binary, *args],
            env=self._build_env(),
            timeout=float(self.config.timeout_seconds),
            cwd=cwd,
        )

    def _build_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.config.config_path is not None:
            env["RMAPI_CONFIG"] = str(self.config.config_path)
        if self.config.trace:
            env["RMAPI_TRACE"] = "1"
        return env


# --------------------------------------------------------------------- helpers


class _AmbiguousCurrentDoc(Exception):
    """More than one home-screen document matched the current-month name."""

    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates
        super().__init__(", ".join(candidates))


class _LsFailed(Exception):
    """``rmapi ls /`` returned a non-zero exit code."""

    def __init__(self, run: CompletedRun) -> None:
        self.run = run
        super().__init__(f"ls failed with exit {run.returncode}")


def _parse_ls_files(stdout: str) -> list[str]:
    """Extract file (``[f]``) names from ``rmapi ls`` text output."""

    names: list[str] = []
    for line in stdout.splitlines():
        match = _LS_LINE_RE.match(line)
        if match and match.group(1) == "f":
            names.append(match.group(2))
    return names


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
