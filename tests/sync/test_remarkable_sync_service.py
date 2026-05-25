from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apps.api.services.remarkable_sync import RemarkableSyncService
from packages.core.models import RenderJob
from packages.remarkable_sync import (
    CompletedRun,
    ManualRemarkableSyncAdapter,
    RmapiConfig,
    RmapiRemarkableSyncAdapter,
)


class FakeRenderJobsRepo:
    def __init__(self, job: RenderJob | None) -> None:
        self.job = job
        self.requested_month: str | None = None

    async def latest_for_month(self, month: str) -> RenderJob | None:
        self.requested_month = month
        return self.job

    async def latest(self) -> RenderJob | None:
        return self.job


@pytest.mark.asyncio
async def test_service_syncs_latest_completed_render_path(tmp_path):
    pdf = tmp_path / "2026-05-habit-dashboard.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    job = RenderJob(
        id="job-1",
        month="2026-05",
        status="completed",
        requested_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        output_path=str(pdf),
    )
    repo = FakeRenderJobsRepo(job)

    result = await RemarkableSyncService(repo).sync_latest_month("2026-05")

    assert repo.requested_month == "2026-05"
    assert result.status == "manual_required"
    assert result.device_mutated is False
    assert result.local_pdf_path == pdf
    assert (
        result.target_path
        == "HabitOS/00 Current/00 Current Month - 2026-05 Habit Dashboard.pdf"
    )


@pytest.mark.asyncio
async def test_service_requires_completed_render_job():
    job = RenderJob(month="2026-05", status="failed")

    with pytest.raises(ValueError, match="not completed"):
        await RemarkableSyncService(FakeRenderJobsRepo(job)).sync_latest_month("2026-05")


@pytest.mark.asyncio
async def test_service_requires_render_job_output_path():
    job = RenderJob(month="2026-05", status="completed")

    with pytest.raises(ValueError, match="no output_path"):
        await RemarkableSyncService(FakeRenderJobsRepo(job)).sync_latest_month("2026-05")


class _StubRunner:
    async def run(self, argv, *, env, timeout):
        return CompletedRun(argv=tuple(argv), returncode=0, stdout="", stderr="")


@pytest.mark.asyncio
async def test_status_reports_manual_adapter():
    repo = FakeRenderJobsRepo(None)
    service = RemarkableSyncService(repo, adapter=ManualRemarkableSyncAdapter())

    info = await service.status()

    assert info["adapter"] == "manual"
    assert info["mode"] == "manual_upload"
    assert "rmapi" not in info


@pytest.mark.asyncio
async def test_status_reports_rmapi_adapter_with_diagnostics(tmp_path):
    repo = FakeRenderJobsRepo(None)
    cfg_path = tmp_path / "rmapi.conf"
    cfg_path.write_text("device_token=abc\n")
    adapter = RmapiRemarkableSyncAdapter(
        RmapiConfig(binary="/nonexistent/rmapi", config_path=cfg_path),
        runner=_StubRunner(),
    )
    service = RemarkableSyncService(repo, adapter=adapter)

    info = await service.status()

    assert info["adapter"] == "rmapi"
    assert info["mode"] == "automated_cloud"
    assert info["rmapi"]["binary"] == "/nonexistent/rmapi"
    assert info["rmapi"]["binary_available"] is False
    assert info["rmapi"]["config_path_readable"] is True
    assert info["rmapi"]["authenticated"] is False
