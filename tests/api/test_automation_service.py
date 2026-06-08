from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pytest

from datetime import date as _date

from apps.api.services.automation import AutomationService
from packages.connectors.base import IntegrationSyncSummary
from packages.connectors.dayone.config import DayOneSettings
from packages.core.models import RenderJob
from packages.remarkable_sync import SyncResult


@dataclass(frozen=True)
class _Settings:
    habitos_timezone: str = "America/New_York"
    reconcile_days: int = 14
    default_whoop_external_user_id: str = "whoop-user-1"
    auto_upload_remarkable: bool = True
    remarkable_dry_run: bool = True
    dayone: DayOneSettings = field(default_factory=lambda: DayOneSettings(lookback_days=4))


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

    async def prepare_current_month_upload(
        self, month: str, pdf_path: Path, dry_run: bool, reset: bool = False
    ):
        self.current_calls.append(
            {"month": month, "pdf_path": str(pdf_path), "dry_run": dry_run, "reset": reset}
        )
        return SyncResult(
            adapter="manual",
            action="upload",
            dry_run=dry_run,
            target_path="01. Habit Tracker.pdf",
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
    assert result["window"]["dayone_start"] == "2026-06-06"
    assert result["window"]["dayone_lookback_days"] == 4
    assert render.calls == [{"month": "2026-06", "triggered_by": "schedule"}]
    assert lifecycle.current_calls[0]["month"] == "2026-06"
    # Mid-month run: not a rollover, so the home document is refreshed in place
    # (merge), never reset.
    assert lifecycle.current_calls[0]["reset"] is False
    assert lifecycle.archive_calls == []
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

    lifecycle = _Lifecycle()
    service.lifecycle = lifecycle

    result = await service.run_nightly_pipeline(today=date(2026, 6, 1))

    assert result["months"]["previous"] == "2026-05"
    assert result["rollover"]["detected"] is True
    assert result["render"]["previous"]["month"] == "2026-05"
    assert result["remarkable"]["archive"]["target_path"] == "HabitOS/2026/Archive/2026-05 Habit Dashboard.pdf"
    # On rollover the current-month upload must reset (fresh new-month page),
    # and the archive must be attempted before it.
    assert lifecycle.archive_calls == [{"month": "2026-05", "dry_run": True}]
    assert lifecycle.current_calls[0]["month"] == "2026-06"
    assert lifecycle.current_calls[0]["reset"] is True


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


class _Dayone:
    """Stub matching the DayOneSyncService.sync_range contract."""

    def __init__(self, *, affected_months: list[str], skipped_reason: str | None = None) -> None:
        self.calls: list[dict] = []
        self.affected_months = affected_months
        self.skipped_reason = skipped_reason

    async def sync_range(self, *, start, end, recompute=False) -> IntegrationSyncSummary:
        self.calls.append({"start": start, "end": end, "recompute": recompute})
        return IntegrationSyncSummary(
            source="day_one",
            account_id=None,
            start=start,
            end=end,
            event_counts_by_type={"journal": len(self.affected_months)},
            inserted=len(self.affected_months),
            updated=0,
            affected_months=list(self.affected_months),
            skipped_reason=self.skipped_reason,
        )


@pytest.mark.asyncio
async def test_run_nightly_pipeline_records_dayone_skipped_when_not_wired():
    runs = _RunsRepo()
    service = AutomationService(
        settings=_Settings(),
        whoop=_Whoop(),
        habits=_Habits(),
        render=_Render(),
        lifecycle=_Lifecycle(),
        runs_repo=runs,
        dayone=None,
    )
    result = await service.run_nightly_pipeline(today=_date(2026, 6, 10))
    assert result["dayone"] == {"skipped_reason": "not_wired"}
    # The runs repo received the skipped dayone summary too.
    assert runs.completed[0]["dayone_summary"]["skipped_reason"] == "not_wired"


@pytest.mark.asyncio
async def test_run_nightly_pipeline_unions_dayone_affected_months():
    # Day One uses its own lookback window and can still report affected
    # months independently of the WHOOP sync result.
    dayone = _Dayone(affected_months=["2026-04", "2026-06"])
    habits = _Habits()
    service = AutomationService(
        settings=_Settings(),
        whoop=_Whoop(),
        habits=habits,
        render=_Render(),
        lifecycle=_Lifecycle(),
        runs_repo=_RunsRepo(),
        dayone=dayone,
    )
    result = await service.run_nightly_pipeline(today=_date(2026, 6, 10))
    # 2026-05 + 2026-06 from WHOOP, 2026-04 from Day One.
    assert result["months"]["affected"] == ["2026-04", "2026-05", "2026-06"]
    assert habits.calls == ["2026-04", "2026-05", "2026-06"]
    assert dayone.calls == [
        {"start": _date(2026, 6, 6), "end": _date(2026, 6, 10), "recompute": False}
    ]
    assert result["window"]["dayone_start"] == "2026-06-06"
    assert result["window"]["dayone_lookback_days"] == 4
    assert result["dayone"]["inserted"] == 2
    assert result["dayone"]["affected_months"] == ["2026-04", "2026-06"]


@pytest.mark.asyncio
async def test_dayone_lookback_can_cover_previous_month_independently():
    dayone = _Dayone(affected_months=["2026-05"])
    habits = _Habits()
    service = AutomationService(
        settings=_Settings(dayone=DayOneSettings(lookback_days=5)),
        whoop=_Whoop(),
        habits=habits,
        render=_Render(),
        lifecycle=_Lifecycle(),
        runs_repo=_RunsRepo(),
        dayone=dayone,
    )

    result = await service.run_nightly_pipeline(today=_date(2026, 6, 2))

    assert dayone.calls == [
        {"start": _date(2026, 5, 28), "end": _date(2026, 6, 2), "recompute": False}
    ]
    assert result["months"]["affected"] == ["2026-05", "2026-06"]
    assert habits.calls == ["2026-05", "2026-06"]


@pytest.mark.asyncio
async def test_run_nightly_pipeline_uses_dayone_specific_lookback_window():
    dayone = _Dayone(affected_months=["2026-06"])
    service = AutomationService(
        settings=_Settings(reconcile_days=14, dayone=DayOneSettings(lookback_days=2)),
        whoop=_Whoop(),
        habits=_Habits(),
        render=_Render(),
        lifecycle=_Lifecycle(),
        runs_repo=_RunsRepo(),
        dayone=dayone,
    )

    result = await service.run_nightly_pipeline(today=_date(2026, 6, 10))

    assert dayone.calls == [
        {"start": _date(2026, 6, 8), "end": _date(2026, 6, 10), "recompute": False}
    ]
    assert result["window"]["start"] == "2026-05-27"
    assert result["window"]["dayone_start"] == "2026-06-08"
    assert result["window"]["dayone_lookback_days"] == 2


@pytest.mark.asyncio
async def test_run_nightly_pipeline_status_summary_drops_privacy_fields():
    # Verifies the summary projected for /automation/status (and persisted)
    # never carries journal_names/tags/entry_uuids.
    dayone = _Dayone(affected_months=["2026-06"])
    runs = _RunsRepo()
    service = AutomationService(
        settings=_Settings(),
        whoop=_Whoop(),
        habits=_Habits(),
        render=_Render(),
        lifecycle=_Lifecycle(),
        runs_repo=runs,
        dayone=dayone,
    )
    result = await service.run_nightly_pipeline(today=_date(2026, 6, 10))
    persisted = runs.completed[0]["dayone_summary"]
    for forbidden in ("journal_names", "journal_ids", "tags", "entry_uuids", "total_word_count"):
        assert forbidden not in result["dayone"]
        assert forbidden not in persisted


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
