from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apps.api.services.remarkable_sync import RemarkableSyncService
from packages.core.models import RenderJob


class FakeRenderJobsRepo:
    def __init__(self, job: RenderJob | None) -> None:
        self.job = job
        self.requested_month: str | None = None

    async def latest_for_month(self, month: str) -> RenderJob | None:
        self.requested_month = month
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
    assert result.target_path == "HabitOS/2026/2026-05 Habit Dashboard.pdf"


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
