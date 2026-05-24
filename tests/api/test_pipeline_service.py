from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from apps.api.services.pipeline import PipelineRenderError, PipelineService
from packages.core.models import RenderJob
from packages.remarkable_sync import SyncResult


class FakeWhoop:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def sync_range(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "external_user_id": kwargs["external_user_id"],
            "start": kwargs["start"].isoformat(),
            "end": kwargs["end"].isoformat(),
            "workouts": 8,
            "sleeps": 28,
            "recoveries": 27,
            "events_written": 63,
            "recomputed_months": [],
            "written": {
                "workouts": {"inserted": 1, "updated": 7},
                "sleeps": {"inserted": 2, "updated": 26},
                "recoveries": {"inserted": 3, "updated": 24},
            },
        }


class FakeHabits:
    async def recompute(self, month: str):
        return {
            "month": month,
            "habits": 6,
            "events": 63,
            "overrides": 0,
            "entries_deleted": 10,
            "entries_written": 120,
        }


class FakeRender:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def render(self, month: str, *, triggered_by: str = "manual"):
        if self.fail:
            raise RuntimeError("playwright exploded")
        return RenderJob(
            id="job-1",
            month=month,
            status="completed",
            output_path=f"data/generated/{month}-habit-dashboard.pdf",
            triggered_by=triggered_by,
        )


class FakeRemarkable:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict] = []

    async def sync_latest_month(self, month: str, *, dry_run: bool = True, update: bool = False):
        self.calls.append({"month": month, "dry_run": dry_run, "update": update})
        if self.fail:
            raise RuntimeError("tablet unavailable")
        return SyncResult(
            adapter="manual",
            action="upload",
            dry_run=dry_run,
            target_path="HabitOS/2026/2026-05 Habit Dashboard.pdf",
            status="manual_required",
            message="ok",
            local_pdf_path=Path("data/generated/2026-05-habit-dashboard.pdf"),
            device_mutated=False,
            instructions=["upload manually"],
        )


@pytest.mark.asyncio
async def test_pipeline_runs_without_upload():
    whoop = FakeWhoop()
    remarkable = FakeRemarkable()
    service = PipelineService(whoop, FakeHabits(), FakeRender(), remarkable)

    result = await service.run_month(
        external_user_id="user-1",
        start=date(2026, 5, 1),
        end=date(2026, 5, 31),
        month="2026-05",
        upload=False,
    )

    assert whoop.calls[0]["recompute"] is False
    assert result["whoop"]["workouts"] == {"inserted": 1, "updated": 7}
    assert result["habits"]["recomputed"] == 120
    assert result["render"]["status"] == "completed"
    assert result["remarkable"] == {"attempted": False, "status": "skipped"}
    assert remarkable.calls == []


@pytest.mark.asyncio
async def test_pipeline_upload_failure_preserves_pdf():
    service = PipelineService(FakeWhoop(), FakeHabits(), FakeRender(), FakeRemarkable(fail=True))

    result = await service.run_month(
        external_user_id="user-1",
        start=date(2026, 5, 1),
        end=date(2026, 5, 31),
        month="2026-05",
        upload=True,
    )

    assert result["render"]["pdf_path"] == "data/generated/2026-05-habit-dashboard.pdf"
    assert result["remarkable"]["attempted"] is True
    assert result["remarkable"]["status"] == "failed"
    assert result["remarkable"]["pdf_preserved"] == "data/generated/2026-05-habit-dashboard.pdf"


@pytest.mark.asyncio
async def test_pipeline_render_failure_skips_upload():
    remarkable = FakeRemarkable()
    service = PipelineService(FakeWhoop(), FakeHabits(), FakeRender(fail=True), remarkable)

    with pytest.raises(PipelineRenderError) as exc:
        await service.run_month(
            external_user_id="user-1",
            start=date(2026, 5, 1),
            end=date(2026, 5, 31),
            month="2026-05",
            upload=True,
        )

    assert exc.value.detail["render"]["status"] == "failed"
    assert exc.value.detail["remarkable"]["status"] == "skipped"
    assert remarkable.calls == []
