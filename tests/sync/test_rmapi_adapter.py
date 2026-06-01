"""Unit tests for the rmapi-backed reMarkable sync adapter.

All subprocess interaction is mediated through a fake runner. No real
rmapi binary is ever spawned by these tests.
"""

from __future__ import annotations

import asyncio
import shutil
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
from packages.remarkable_sync.rmdoc import read_visible_name
from tests.sync._bundle_factory import make_pdf, make_rmdoc

CURRENT = "01. Habit Tracker"


# --------------------------------------------------------------------- fakes


@dataclass
class _Call:
    argv: list[str]
    env: dict[str, str]
    timeout: float
    cwd: str | None


@dataclass
class FakeRunner:
    """Records calls; serves scripted responses indexed by argv tail.

    Scripted responses map an argv tuple (e.g. ``("stat", "/HabitOS")``)
    to a ``CompletedRun``, a callable ``(argv, env, timeout, cwd)``, or an
    exception that the runner will raise on that invocation.
    """

    responses: dict[tuple[str, ...], object] = field(default_factory=dict)
    default: object = None
    calls: list[_Call] = field(default_factory=list)

    async def run(
        self,
        argv: list[str],
        *,
        env: dict[str, str],
        timeout: float,
        cwd: str | None = None,
    ) -> CompletedRun:
        self.calls.append(_Call(argv=list(argv), env=dict(env), timeout=timeout, cwd=cwd))
        tail = tuple(argv[1:])
        key = self._best_key(tail)
        response = self.responses.get(key, self.default)
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            return response(argv, env, timeout, cwd)
        if isinstance(response, CompletedRun):
            return response
        return CompletedRun(argv=tuple(argv), returncode=0, stdout="", stderr="")

    def _best_key(self, tail: tuple[str, ...]) -> tuple[str, ...]:
        for length in range(len(tail), 0, -1):
            prefix = tail[:length]
            if prefix in self.responses:
                return prefix
        return tail

    def put_calls(self) -> list[_Call]:
        return [c for c in self.calls if c.argv[1:2] == ["put"]]


def _make_pdf(tmp_path: Path, name: str = "2026-05-habit-dashboard.pdf", pages: int = 1) -> Path:
    return make_pdf(tmp_path / name, pages)


def _make_config(**overrides) -> RmapiConfig:
    defaults = dict(
        binary="rmapi",
        config_path=None,
        timeout_seconds=60,
        trace=False,
        replace_existing_current=False,
        preserve_annotations=True,
        machine_root="HabitOS",
    )
    defaults.update(overrides)
    return RmapiConfig(**defaults)


def _ok(stdout: str = "", stderr: str = "") -> CompletedRun:
    return CompletedRun(argv=(), returncode=0, stdout=stdout, stderr=stderr)


def _fail(stderr: str = "boom", returncode: int = 1) -> CompletedRun:
    return CompletedRun(argv=(), returncode=returncode, stdout="", stderr=stderr)


def _ls(*files: str) -> CompletedRun:
    lines = [f"[f]\t{name}" for name in files] + ["[d]\tHabitOS"]
    return _ok(stdout="\n".join(lines) + "\n")


def _current_request(pdf: Path, dry_run: bool = False) -> SyncRequest:
    target = build_current_month_target("2026-05")
    return SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=dry_run,
    )


# ----------------------------------------------------------------- dry run


@pytest.mark.asyncio
async def test_dry_run_does_not_call_rmapi(tmp_path):
    runner = FakeRunner()
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(_make_pdf(tmp_path), dry_run=True))

    assert result.status == "planned"
    assert result.device_mutated is False
    assert runner.calls == []
    assert any("planned" in line for line in result.instructions)


# ------------------------------------------------------------- safety / scope


@pytest.mark.asyncio
async def test_rejects_path_outside_machine_root(tmp_path):
    request = SyncRequest(
        local_pdf_path=_make_pdf(tmp_path),
        document_name="Stolen",
        folder_path=("Documents",),
        dry_run=False,
    )
    runner = FakeRunner()
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    assert result.status == "unsupported"
    assert runner.calls == []


@pytest.mark.asyncio
async def test_rejects_wrong_home_screen_document_name(tmp_path):
    request = SyncRequest(
        local_pdf_path=_make_pdf(tmp_path),
        document_name="Random Notebook",
        folder_path=(),
        dry_run=False,
    )
    runner = FakeRunner()
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    assert result.status == "unsupported"
    assert runner.calls == []


@pytest.mark.asyncio
async def test_rejects_path_with_wrong_machine_root(tmp_path):
    request = SyncRequest(
        local_pdf_path=_make_pdf(tmp_path),
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
    runner = FakeRunner(default=FileNotFoundError("rmapi"))
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(_make_pdf(tmp_path)))

    assert result.status == "not_configured"
    assert "rmapi binary not found" in result.message
    assert result.device_mutated is False


@pytest.mark.asyncio
async def test_diagnostics_reports_binary_absent_when_path_missing(tmp_path):
    runner = FakeRunner()
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(binary="/nonexistent/rmapi"), runner=runner
    )

    info = await adapter.diagnostics()

    assert info["binary_available"] is False
    assert info["authenticated"] is False
    assert info["preserve_annotations"] is True
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


# ------------------------------------------------------------- archive flow


@pytest.mark.asyncio
async def test_archive_ensures_folder_chain_and_uploads(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_archive_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))
    responses = {
        ("stat", "/HabitOS"): _fail("missing"),
        ("stat", "/HabitOS/2026"): _fail("missing"),
        ("stat", "/HabitOS/2026/Archive"): _fail("missing"),
        ("stat", target_remote): _fail("missing"),
    }
    runner = FakeRunner(responses=responses, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(request)

    cmds = [tuple(call.argv[1:]) for call in runner.calls]
    assert ("mkdir", "/HabitOS") in cmds
    assert ("mkdir", "/HabitOS/2026/Archive") in cmds
    assert result.status == "uploaded"
    assert result.device_mutated is True


@pytest.mark.asyncio
async def test_archive_skips_mkdir_when_folder_exists(tmp_path):
    pdf = _make_pdf(tmp_path)
    target = build_archive_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
    )
    target_remote = "/" + "/".join((*target.folder_path, f"{target.document_name}.pdf"))
    responses = {
        ("stat", "/HabitOS"): _ok(),
        ("stat", "/HabitOS/2026"): _ok(),
        ("stat", "/HabitOS/2026/Archive"): _ok(),
        ("stat", target_remote): _fail("missing"),
    }
    runner = FakeRunner(responses=responses, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    await adapter.upload_pdf(request)
    cmds = [tuple(call.argv[1:]) for call in runner.calls]
    assert ("mkdir", "/HabitOS") not in cmds
    assert ("mkdir", "/HabitOS/2026/Archive") not in cmds


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
    assert runner.put_calls() == []


# ------------------------------------------------------------- current flow


@pytest.mark.asyncio
async def test_current_absent_creates_named_document(tmp_path):
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(responses={("ls", "/"): _ls("Some Other Doc")}, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(pdf))

    puts = runner.put_calls()
    assert len(puts) == 1
    assert "--force" not in puts[0].argv
    assert puts[0].argv[-1] == "/"
    # Staged under the canonical home-screen name, not the raw render filename.
    assert Path(puts[0].argv[-2]).name == f"{CURRENT}.pdf"
    assert result.status == "uploaded"
    assert result.device_mutated is True


@pytest.mark.asyncio
async def test_current_present_merges_preserving_annotations(tmp_path):
    rendered = _make_pdf(tmp_path, "rendered.pdf", pages=3)
    bundle, _ = make_rmdoc(tmp_path / "device.rmdoc", doc_id=CURRENT, n_pages=3, rm_count=2)

    def _get(argv, env, timeout, cwd):
        name = argv[-1].lstrip("/")
        shutil.copyfile(bundle, Path(cwd) / f"{name}.rmdoc")
        return _ok()

    runner = FakeRunner(
        responses={("ls", "/"): _ls(CURRENT), ("get",): _get},
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(rendered))

    assert result.status == "updated"
    assert result.device_mutated is True
    assert "preserving annotations" in result.message
    assert "2 ink file" in result.message
    puts = runner.put_calls()
    assert len(puts) == 1
    assert "--force" in puts[0].argv
    assert puts[0].argv[-1] == "/"
    assert Path(puts[0].argv[-2]).name == f"{CURRENT}.rmdoc"


@pytest.mark.asyncio
async def test_current_present_month_labelled_name_is_resolved(tmp_path):
    rendered = _make_pdf(tmp_path, "rendered.pdf", pages=3)
    labelled = f"{CURRENT} | May 2026"
    bundle, _ = make_rmdoc(tmp_path / "device.rmdoc", doc_id=labelled, n_pages=3, rm_count=1)

    def _get(argv, env, timeout, cwd):
        name = argv[-1].lstrip("/")
        shutil.copyfile(bundle, Path(cwd) / f"{name}.rmdoc")
        return _ok()

    runner = FakeRunner(
        responses={("ls", "/"): _ls(labelled, "2. Habit Tracker"), ("get",): _get},
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(rendered))

    assert result.status == "updated"
    get_calls = [c for c in runner.calls if c.argv[1:2] == ["get"]]
    assert get_calls[0].argv[-1] == f"/{labelled}"


@pytest.mark.asyncio
async def test_current_merge_aborts_on_page_count_drift(tmp_path):
    rendered = _make_pdf(tmp_path, "rendered.pdf", pages=2)  # device has 3
    bundle, _ = make_rmdoc(tmp_path / "device.rmdoc", doc_id=CURRENT, n_pages=3, rm_count=1)

    def _get(argv, env, timeout, cwd):
        name = argv[-1].lstrip("/")
        shutil.copyfile(bundle, Path(cwd) / f"{name}.rmdoc")
        return _ok()

    runner = FakeRunner(
        responses={("ls", "/"): _ls(CURRENT), ("get",): _get},
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(rendered))

    assert result.status == "unsupported"
    assert result.device_mutated is False
    # Crucially: no upload happened, so ink is untouched.
    assert runner.put_calls() == []


@pytest.mark.asyncio
async def test_current_present_with_replace_uses_force_named_put(tmp_path):
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(responses={("ls", "/"): _ls(CURRENT)}, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(replace_existing_current=True), runner=runner
    )

    result = await adapter.upload_pdf(_current_request(pdf))

    puts = runner.put_calls()
    assert len(puts) == 1
    assert "--force" in puts[0].argv
    assert Path(puts[0].argv[-2]).name == f"{CURRENT}.pdf"
    # No get/swap when doing a destructive reset.
    assert not any(c.argv[1:2] == ["get"] for c in runner.calls)
    assert result.status == "updated"
    assert "dropped" in result.message


@pytest.mark.asyncio
async def test_current_present_both_flags_off_refuses(tmp_path):
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(responses={("ls", "/"): _ls(CURRENT)}, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(preserve_annotations=False, replace_existing_current=False),
        runner=runner,
    )

    result = await adapter.upload_pdf(_current_request(pdf))

    assert result.status == "unsupported"
    assert result.device_mutated is False
    assert runner.put_calls() == []


@pytest.mark.asyncio
async def test_current_ambiguous_match_refuses(tmp_path):
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(
        responses={("ls", "/"): _ls(f"{CURRENT} | May 2026", f"{CURRENT} | Jun 2026")},
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(pdf))

    assert result.status == "unsupported"
    assert "Multiple" in result.message
    assert runner.put_calls() == []


@pytest.mark.asyncio
async def test_current_ls_failure_reports_failed(tmp_path):
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(responses={("ls", "/"): _fail("not logged in")})
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(pdf))

    assert result.status == "failed"
    assert result.device_mutated is False
    assert runner.put_calls() == []


# ------------------------------------------------------------- failure modes


@pytest.mark.asyncio
async def test_put_failure_records_failed_status(tmp_path):
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(
        responses={("ls", "/"): _ls("Some Other Doc"), ("put",): _fail("network down")},
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(pdf))

    assert result.status == "failed"
    assert result.device_mutated is False
    assert any("network down" in line for line in result.instructions)


@pytest.mark.asyncio
async def test_timeout_records_failed_status(tmp_path):
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(default=asyncio.TimeoutError())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await adapter.upload_pdf(_current_request(pdf))

    assert result.status == "failed"
    assert "timed out" in result.message.lower()


# --------------------------------------------------------- rollover reset


@pytest.mark.asyncio
async def test_reset_force_replaces_current_without_merge(tmp_path):
    # At month rollover the home document must be reset to a fresh page: a
    # force put of the PDF, never a get+swap merge (which would keep last
    # month's ink and abort on the page-count change).
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(responses={("ls", "/"): _ls(CURRENT)}, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    target = build_current_month_target("2026-06")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
        reset=True,
    )
    result = await adapter.upload_pdf(request)

    assert result.status == "updated"
    assert result.device_mutated is True
    assert not any(c.argv[1:2] == ["get"] for c in runner.calls)
    puts = runner.put_calls()
    assert len(puts) == 1
    assert "--force" in puts[0].argv
    assert Path(puts[0].argv[-2]).name == f"{CURRENT}.pdf"


@pytest.mark.asyncio
async def test_reset_when_absent_creates_fresh_document(tmp_path):
    pdf = _make_pdf(tmp_path)
    runner = FakeRunner(responses={("ls", "/"): _ls("Some Other Doc")}, default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    target = build_current_month_target("2026-06")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=False,
        reset=True,
    )
    result = await adapter.upload_pdf(request)

    assert result.status == "uploaded"
    puts = runner.put_calls()
    assert len(puts) == 1
    assert "--force" not in puts[0].argv


# ------------------------------------------------- archive device document


def _archive_target():
    return build_archive_month_target("2026-05")


async def _archive(adapter):
    target = _archive_target()
    return await adapter.archive_device_document(
        source_document_name=CURRENT,
        target_folder_path=target.folder_path,
        target_document_name=target.document_name,
        dry_run=False,
    )


@pytest.mark.asyncio
async def test_archive_device_document_downloads_renames_and_uploads(tmp_path):
    # The archive snapshots the on-device home document *with its ink* and
    # uploads it under the archive name — never a fresh annotation-free PDF.
    bundle, _ = make_rmdoc(tmp_path / "device.rmdoc", doc_id=CURRENT, n_pages=3, rm_count=2)
    target = _archive_target()
    archive_folder = "/" + "/".join(target.folder_path)

    def _get(argv, env, timeout, cwd):
        name = argv[-1].lstrip("/")
        shutil.copyfile(bundle, Path(cwd) / f"{name}.rmdoc")
        return _ok()

    seen: dict[str, object] = {}

    def _put(argv, env, timeout, cwd):
        staged = Path(argv[-2])
        seen["staged_name"] = staged.name
        seen["visible_name"] = read_visible_name(staged)
        seen["folder"] = argv[-1]
        return _ok()

    runner = FakeRunner(
        responses={
            ("ls", "/"): _ls(CURRENT),
            # Archive folder is empty → target not yet archived.
            ("ls", archive_folder): _ok(stdout=""),
            ("get",): _get,
            ("put",): _put,
        },
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await _archive(adapter)

    assert result.status == "uploaded"
    assert result.device_mutated is True
    # Uploaded as an .rmdoc bundle (carries ink), renamed for the archive, into
    # the archive folder.
    assert seen["staged_name"] == f"{target.document_name}.rmdoc"
    assert seen["visible_name"] == target.document_name
    assert seen["folder"] == archive_folder


@pytest.mark.asyncio
async def test_archive_device_document_is_idempotent_when_target_exists(tmp_path):
    # Archives are frozen. A second rollover run (e.g. catch-up + cron) must not
    # re-download or duplicate the snapshot.
    target = _archive_target()
    archive_folder = "/" + "/".join(target.folder_path)
    runner = FakeRunner(
        responses={
            ("ls", "/"): _ls(CURRENT),
            # Target already present in the archive folder.
            ("ls", archive_folder): _ls(target.document_name),
        },
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await _archive(adapter)

    assert result.status == "uploaded"
    assert result.device_mutated is False
    assert "already exists" in result.message
    assert not any(c.argv[1:2] == ["get"] for c in runner.calls)
    assert runner.put_calls() == []


@pytest.mark.asyncio
async def test_archive_device_document_source_missing_fails(tmp_path):
    target = _archive_target()
    archive_folder = "/" + "/".join(target.folder_path)
    runner = FakeRunner(
        responses={
            ("ls", "/"): _ls("Some Other Doc"),
            ("ls", archive_folder): _ok(stdout=""),
        },
        default=_ok(),
    )
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    result = await _archive(adapter)

    assert result.status == "failed"
    assert result.device_mutated is False
    assert runner.put_calls() == []


@pytest.mark.asyncio
async def test_archive_device_document_dry_run_plans_only(tmp_path):
    runner = FakeRunner(default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)
    target = _archive_target()

    result = await adapter.archive_device_document(
        source_document_name=CURRENT,
        target_folder_path=target.folder_path,
        target_document_name=target.document_name,
        dry_run=True,
    )

    assert result.status == "planned"
    assert result.device_mutated is False
    assert runner.calls == []


# ----------------------------------------------------------------- env


@pytest.mark.asyncio
async def test_env_includes_rmapi_config_and_trace(tmp_path):
    runner = FakeRunner(default=_ok())
    cfg_path = tmp_path / "rmapi.conf"
    cfg_path.write_text("device_token=abc\n")
    adapter = RmapiRemarkableSyncAdapter(
        _make_config(config_path=cfg_path, trace=True), runner=runner
    )

    await adapter.upload_pdf(_current_request(_make_pdf(tmp_path)))

    assert runner.calls, "expected at least one rmapi call"
    env = runner.calls[0].env
    assert env.get("RMAPI_CONFIG") == str(cfg_path)
    assert env.get("RMAPI_TRACE") == "1"


@pytest.mark.asyncio
async def test_env_omits_config_and_trace_when_unset(tmp_path):
    runner = FakeRunner(default=_ok())
    adapter = RmapiRemarkableSyncAdapter(_make_config(), runner=runner)

    await adapter.upload_pdf(_current_request(_make_pdf(tmp_path)))

    env = runner.calls[0].env
    assert "RMAPI_CONFIG" not in env
    assert env.get("RMAPI_TRACE") != "1"


# ------------------------------------------------------------- manual passes


@pytest.mark.asyncio
async def test_manual_adapter_unchanged(tmp_path):
    manual = ManualRemarkableSyncAdapter()

    result = await manual.upload_pdf(_current_request(_make_pdf(tmp_path)))

    assert result.adapter == "manual"
    assert result.status == "manual_required"
    assert result.device_mutated is False
