"""Unit tests for the rmapi-backed reMarkable sync adapter.

All subprocess interaction is mediated through a fake runner. No real
rmapi binary is ever spawned by these tests.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from packages.remarkable_sync import (
    CompletedRun,
    ManualRemarkableSyncAdapter,
    RmapiConfig,
    RmapiRemarkableSyncAdapter,
    SyncRequest,
    build_archive_month_target,
    build_current_month_target,
)


# --------------------------------------------------------------------- fakes


@dataclass
class _Call:
    argv: list[str]
    env: dict[str, str]
    timeout: float


@dataclass
class FakeRunner:
    """Records calls; serves scripted responses indexed by argv tail.

    Scripted responses map an argv tuple (e.g. ``("stat", "/HabitOS")``)
    to a ``CompletedRun`` or a callable/exception that the runner will
    raise on that invocation.
    """

    responses: dict[tuple[str, ...], object] = field(default_factory=dict)
    default: object = None
    calls: list[_Call] = field(default_factory=list)

    async def run(self, argv: list[str], *, env: dict[str, str], timeout: float) -> CompletedRun:
        self.calls.append(_Call(argv=list(argv), env=dict(env), timeout=timeout))
        # tail = everything after the binary path
        tail = tuple(argv[1:])
        key = self._best_key(tail)
        response = self.responses.get(key, self.default)
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            return response(argv, env, timeout)
        if isinstance(response, CompletedRun):
            return response
        # Default: exit 0 with empty output.
        return CompletedRun(argv=tuple(argv), returncode=0, stdout="", stderr="")

    def _best_key(self, tail: tuple[str, ...]) -> tuple[str, ...]:
        for length in range(len(tail), 0, -1):
            prefix = tail[:length]
            if prefix in self.responses:
                return prefix
        return tail


def _make_pdf(tmp_path: Path, name: str = "2026-05-habit-dashboard.pdf") -> Path:
    pdf = tmp_path / name
    pdf.write_bytes(b"%PDF-1.4\n")
    return pdf


def _make_config(**overrides) -> RmapiConfig:
    defaults = dict(
        binary="rmapi",
        config_path=None,
        timeout_seconds=60,
        trace=False,
        replace_existing_current=False,
        machine_root="HabitOS",
    )
    defaults.update(overrides)
    return RmapiConfig(**defaults)


def _ok(stdout: str = "", stderr: str = "") -> CompletedRun:
    return CompletedRun(argv=(), returncode=0, stdout=stdout, stderr=stderr)


def _fail(stderr: str = "boom", returncode: int = 1) -> CompletedRun:
    return CompletedRun(argv=(), returncode=returncode, stdout="", stderr=stderr)


# ----------------------------------------------------------------- dry run


@pytest.mark.asyncio
async def test_dry_run_does_not_call_rmapi(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=True,
    )
    runner = FakeRunner()
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    assert result.status == "planned"
    assert result.device_mutated is False
    assert runner.calls == []
    assert any("planned:" in line for line in result.instructions)


# ------------------------------------------------------------- safety / scope


@pytest.mark.asyncio
async def test_rejects_path_outside_machine_root(tmp_path):
    pdf = _make_pdf(tmp_path)
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name="Stolen",
        folder_path=("Documents",),
        dry_run=False,
    )
    runner = FakeRunner()
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    assert result.status == "unsupported"
    assert result.device_mutated is False
    assert runner.calls == []


@pytest.mark.asyncio
async def test_rejects_path_with_wrong_machine_root(tmp_path):
    pdf = _make_pdf(tmp_path)
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name="foo",
        folder_path=("Notes", "00 Current"),
        dry_run=False,
    )
    runner = FakeRunner()
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    assert (await adapter.upload_pdf(request)).status == "unsupported"
    assert runner.calls == []


# ------------------------------------------------------------- diagnostics


@pytest.mark.asyncio
async def test_missing_binary_returns_diagnostic(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    runner = FakeRunner(default=FileNotFoundError("rmapi"))
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    assert result.status == "not_configured"
    assert "rmapi binary not found" in result.message
    assert result.device_mutated is False


@pytest.mark.asyncio
async def test_diagnostics_reports_binary_absent_when_path_missing(tmp_path):
    runner = FakeRunner()
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(binary="/nonexistent/rmapi"),
        runner=runner,
    )

    info = await adapter.diagnostics()

    assert info["binary_available"] is False
    assert info["authenticated"] is False
    # ls should not have been called since the binary was unresolved.
    assert runner.calls == []


@pytest.mark.asyncio
async def test_diagnostics_reports_config_readability(tmp_path):
    config_file = tmp_path / "rmapi.conf"
    config_file.write_text("device_token=abc\n")
    runner = FakeRunner(default=_ok())
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(binary="/nonexistent/rmapi", config_path=config_file),
        runner=runner,
    )

    info = await adapter.diagnostics()

    assert info["config_path"] == str(config_file)
    assert info["config_path_readable"] is True


# ------------------------------------------------------------- folder chain


@pytest.mark.asyncio
async def test_ensures_folder_chain_creates_missing_segments(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))

    responses = {
        ("stat", "/HabitOS"): _fail("missing"),
        ("mkdir", "/HabitOS"): _ok(),
        ("stat", "/HabitOS/00 Current"): _fail("missing"),
        ("mkdir", "/HabitOS/00 Current"): _ok(),
        ("stat", target_remote): _fail("missing"),  # doc absent
    }
    runner = FakeRunner(responses=responses, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    cmds = [tuple(call.argv[1:]) for call in runner.calls]
    assert ("mkdir", "/HabitOS") in cmds
    assert ("mkdir", "/HabitOS/00 Current") in cmds
    assert result.status == "uploaded"
    assert result.device_mutated is True


@pytest.mark.asyncio
async def test_skips_mkdir_when_folder_exists(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))
    responses = {
        ("stat", "/HabitOS"): _ok(),
        ("stat", "/HabitOS/00 Current"): _ok(),
        ("stat", target_remote): _fail("missing"),
    }
    runner = FakeRunner(responses=responses, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    await adapter.upload_pdf(request)
    cmds = [tuple(call.argv[1:]) for call in runner.calls]
    assert ("mkdir", "/HabitOS") not in cmds
    assert ("mkdir", "/HabitOS/00 Current") not in cmds


# ------------------------------------------------------------- upload paths


@pytest.mark.asyncio
async def test_upload_when_target_absent_uses_plain_put(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))
    runner = FakeRunner(
        responses={
            ("stat", "/HabitOS"): _ok(),
            ("stat", "/HabitOS/00 Current"): _ok(),
            ("stat", target_remote): _fail("missing"),
        },
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    put_calls = [c for c in runner.calls if c.argv[1:2] == ["put"]]
    assert len(put_calls) == 1
    assert "--force" not in put_calls[0].argv
    assert str(pdf) in put_calls[0].argv
    assert "/HabitOS/00 Current" in put_calls[0].argv
    assert result.status == "uploaded"
    assert result.device_mutated is True


@pytest.mark.asyncio
async def test_upload_current_target_present_no_replace_refuses(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))
    runner = FakeRunner(
        responses={
            ("stat", "/HabitOS"): _ok(),
            ("stat", "/HabitOS/00 Current"): _ok(),
            ("stat", target_remote): _ok(),  # exists
        },
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(replace_existing_current=False), runner=runner
    )

    result = await adapter.upload_pdf(request)

    assert result.status == "unsupported"
    assert result.device_mutated is False
    assert not any(c.argv[1:2] == ["put"] for c in runner.calls)


@pytest.mark.asyncio
async def test_upload_current_target_present_with_replace_uses_force(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))
    runner = FakeRunner(
        responses={
            ("stat", "/HabitOS"): _ok(),
            ("stat", "/HabitOS/00 Current"): _ok(),
            ("stat", target_remote): _ok(),  # exists
        },
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(replace_existing_current=True), runner=runner
    )

    result = await adapter.upload_pdf(request)

    put = [c for c in runner.calls if c.argv[1:2] == ["put"]]
    assert len(put) == 1
    assert "--force" in put[0].argv
    assert result.status == "updated"
    assert result.device_mutated is True


@pytest.mark.asyncio
async def test_archive_refuses_overwrite_even_with_replace(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_archive_month_target("2026-04")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))
    runner = FakeRunner(
        responses={
            ("stat", "/HabitOS"): _ok(),
            ("stat", "/HabitOS/2026"): _ok(),
            ("stat", "/HabitOS/2026/Archive"): _ok(),
            ("stat", target_remote): _ok(),  # exists
        },
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(replace_existing_current=True), runner=runner
    )

    result = await adapter.upload_pdf(request)

    assert result.status == "unsupported"
    assert "frozen" in result.message
    assert not any(c.argv[1:2] == ["put"] for c in runner.calls)


# ------------------------------------------------------------- failure modes


@pytest.mark.asyncio
async def test_put_failure_records_failed_status(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))
    runner = FakeRunner(
        responses={
            ("stat", "/HabitOS"): _ok(),
            ("stat", "/HabitOS/00 Current"): _ok(),
            ("stat", target_remote): _fail("missing"),
            ("put",): _fail("network down"),
        },
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    assert result.status == "failed"
    assert result.device_mutated is False
    assert any("network down" in line for line in result.instructions)


@pytest.mark.asyncio
async def test_timeout_records_failed_status(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    runner = FakeRunner(default=asyncio.TimeoutError())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    assert result.status == "failed"
    assert "timed out" in result.message.lower()


# ----------------------------------------------------------------- env


@pytest.mark.asyncio
async def test_env_includes_rmapi_config_and_trace(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    runner = FakeRunner(default=_ok())
    cfg_path = tmp_path / "rmapi.conf"
    cfg_path.write_text("device_token=abc\n")
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(config_path=cfg_path, trace=True), runner=runner
    )

    await adapter.upload_pdf(request)

    assert runner.calls, "expected at least one rmapi call"
    env = runner.calls[0].env
    assert env.get("RMAPI_CONFIG") == str(cfg_path)
    assert env.get("RMAPI_TRACE") == "1"


@pytest.mark.asyncio
async def test_env_omits_config_and_trace_when_unset(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    runner = FakeRunner(default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    await adapter.upload_pdf(request)

    env = runner.calls[0].env
    assert "RMAPI_CONFIG" not in env
    assert env.get("RMAPI_TRACE") != "1"


# ------------------------------------------------------------- manual passes


@pytest.mark.asyncio
async def test_manual_adapter_unchanged(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    manual = ManualRemarkableSyncAdapter()

    result = await manual.upload_pdf(request)

    assert result.adapter == "manual"
    assert result.status == "manual_required"
    assert result.device_mutated is False
