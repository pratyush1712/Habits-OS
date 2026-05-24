from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from apps.api.services.automation import AutomationService
from packages.core.models import RenderJob
from packages.remarkable_sync import SyncResult


@dataclass(frozen=True)
class _Settings:
    habitos_timezone: str = "America/New_York"
    reconcile_days: int = 14
    default_whoop_external_user_id: str = "whoop-user-1"
    auto_upload_remarkable: bool = True
    remarkable_dry_run: bool = True


class _Whoop:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def sync_range(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "events_written": 5,
            "workouts": 1,
            "sleeps": 2,
            "recoveries": 2,
            "written": {
                "workouts": {"inserted": 1, "updated": 0},
                "sleeps": {"inserted": 2, "updated": 0},
                "recoveries": {"inserted": 2, "updated": 0},
            },
            "recomputed_months": [],
        }


class _Habits:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def recompute(self, month: str):
        self.calls.append(month)
        return {"month": month, "entries_written": 30, "entries_deleted": 5}


class _Render:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def render(self, month: str, *, triggered_by: str = "manual"):
        self.calls.append({"month": month, "triggered_by": triggered_by})
        return RenderJob(
            id=f"render-{month}",
            month=month,
            status="completed",
            output_path=f"data/generated/{month}-habit-dashboard.pdf",
            triggered_by=triggered_by,
        )


class _Lifecycle:
    def __init__(self) -> None:
        self.current_calls: list[dict] = []
        self.archive_calls: list[dict] = []

    async def prepare_current_month_upload(self, month: str, pdf_path: Path, dry_run: bool):
        self.current_calls.append({"month": month, "pdf_path": str(pdf_path), "dry_run": dry_run})
        return SyncResult(
            adapter="manual",
            action="upload",
            dry_run=dry_run,
            target_path=f"HabitOS/00 Current/00 Current Month - {month} Habit Dashboard.pdf",
            status="manual_required",
            message="manual",
            local_pdf_path=pdf_path,
            device_mutated=False,
            instructions=["upload manually"],
        )

    async def prepare_archive_previous_month(self, month: str, dry_run: bool):
        self.archive_calls.append({"month": month, "dry_run": dry_run})
        return SyncResult(
            adapter="manual",
            action="upload",
            dry_run=dry_run,
            target_path=f"HabitOS/{month[:4]}/Archive/{month} Habit Dashboard.pdf",
            status="manual_required",
            message="manual",
            local_pdf_path=Path(f"data/generated/{month}-habit-dashboard.pdf"),
            device_mutated=False,
            instructions=["archive manually"],
        )


class _RunsRepo:
    def __init__(self) -> None:
        self.created = []
        self.completed = []
        self.failed = []

    async def create(self, run) -> str:
        self.created.append(run)
        return "run-1"

    async def complete(self, run_id: str, **kwargs) -> bool:
        self.completed.append({"run_id": run_id, **kwargs})
        return True

    async def fail(self, run_id: str, **kwargs) -> bool:
        self.failed.append({"run_id": run_id, **kwargs})
        return True


@pytest.mark.asyncio
async def test_run_nightly_pipeline_computes_window_and_affected_months():
    whoop = _Whoop()
    habits = _Habits()
    render = _Render()
    lifecycle = _Lifecycle()
    runs = _RunsRepo()
    service = AutomationService(
        settings=_Settings(),
        whoop=whoop,
        habits=habits,
        render=render,
        lifecycle=lifecycle,
        runs_repo=runs,
    )

    result = await service.run_nightly_pipeline(today=date(2026, 6, 10))

    assert whoop.calls == [
        {
            "external_user_id": "whoop-user-1",
            "start": date(2026, 5, 27),
            "end": date(2026, 6, 10),
            "recompute": False,
        }
    ]
    assert habits.calls == ["2026-05", "2026-06"]
    assert render.calls == [{"month": "2026-06", "triggered_by": "schedule"}]
    assert lifecycle.current_calls[0]["month"] == "2026-06"
    assert result["months"]["affected"] == ["2026-05", "2026-06"]
    assert runs.completed[0]["run_id"] == "run-1"


@pytest.mark.asyncio
async def test_run_nightly_pipeline_handles_month_rollover():
    service = AutomationService(
        settings=_Settings(),
        whoop=_Whoop(),
        habits=_Habits(),
        render=_Render(),
        lifecycle=_Lifecycle(),
        runs_repo=_RunsRepo(),
    )

    result = await service.run_nightly_pipeline(today=date(2026, 6, 1))

    assert result["months"]["previous"] == "2026-05"
    assert result["rollover"]["detected"] is True
    assert result["render"]["previous"]["month"] == "2026-05"
    assert result["remarkable"]["archive"]["target_path"] == "HabitOS/2026/Archive/2026-05 Habit Dashboard.pdf"


@pytest.mark.asyncio
async def test_run_nightly_pipeline_fails_without_default_user():
    runs = _RunsRepo()
    service = AutomationService(
        settings=_Settings(default_whoop_external_user_id=""),
        whoop=_Whoop(),
        habits=_Habits(),
        render=_Render(),
        lifecycle=_Lifecycle(),
        runs_repo=runs,
    )

    with pytest.raises(ValueError, match="HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID"):
        await service.run_nightly_pipeline(today=date(2026, 6, 10))

    assert runs.failed[0]["run_id"] == "run-1"


@pytest.mark.asyncio
async def test_run_month_rollover_validates_order():
    service = AutomationService(
        settings=_Settings(),
        whoop=_Whoop(),
        habits=_Habits(),
        render=_Render(),
        lifecycle=_Lifecycle(),
        runs_repo=_RunsRepo(),
    )

    with pytest.raises(ValueError, match="must be the month immediately after"):
        await service.run_month_rollover("2026-06", "2026-08", dry_run=True)
