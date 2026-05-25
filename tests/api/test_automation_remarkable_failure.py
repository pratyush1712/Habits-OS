"""Automation continues when rmapi upload fails.

These tests prove that a reMarkable upload exception is captured as a
failed sync summary inside ``automation_runs.remarkable_summary`` and
does NOT abort the run, erase the render result, or surface as a raised
exception. Render history must remain intact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from apps.api.services.automation import AutomationService
from packages.core.models import RenderJob


@dataclass(frozen=True)
class _Settings:
    habitos_timezone: str = "America/New_York"
    reconcile_days: int = 14
    default_whoop_external_user_id: str = "whoop-user-1"
    auto_upload_remarkable: bool = True
    remarkable_dry_run: bool = False


class _Whoop:
    async def sync_range(self, **kwargs):
        return {
            "events_written": 0,
            "workouts": 0,
            "sleeps": 0,
            "recoveries": 0,
            "written": {
                "workouts": {"inserted": 0, "updated": 0},
                "sleeps": {"inserted": 0, "updated": 0},
                "recoveries": {"inserted": 0, "updated": 0},
            },
            "recomputed_months": [],
        }


class _Habits:
    async def recompute(self, month: str):
        return {"month": month, "entries_written": 1, "entries_deleted": 0}


class _Render:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def render(self, month: str, *, triggered_by: str = "manual"):
        self.calls.append(month)
        return RenderJob(
            id=f"render-{month}",
            month=month,
            status="completed",
            output_path=f"data/generated/{month}-habit-dashboard.pdf",
            triggered_by=triggered_by,
        )


class _ExplodingLifecycle:
    """Lifecycle that raises on every upload, simulating rmapi failure."""

    async def prepare_current_month_upload(self, month, pdf_path: Path, dry_run: bool):
        raise RuntimeError("rmapi cloud unreachable")

    async def prepare_archive_previous_month(self, month: str, dry_run: bool):
        raise RuntimeError("rmapi archive upload failed")


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
async def test_nightly_continues_when_current_upload_fails():
    render = _Render()
    runs = _RunsRepo()
    service = AutomationService(
        settings=_Settings(),
        whoop=_Whoop(),
        habits=_Habits(),
        render=render,
        lifecycle=_ExplodingLifecycle(),
        runs_repo=runs,
    )

    result = await service.run_nightly_pipeline(today=date(2026, 6, 10))

    # Render still happened; the run is marked complete (not failed).
    assert render.calls == ["2026-06"]
    assert runs.completed and not runs.failed
    # The remarkable summary records failure but does not bubble.
    current = result["remarkable"]["current"]
    assert current["status"] == "failed"
    assert current["device_mutated"] is False
    assert "rmapi cloud unreachable" in current["message"]
    # Render summary is preserved.
    assert result["render"]["current"]["status"] == "completed"


@pytest.mark.asyncio
async def test_nightly_rollover_continues_when_archive_upload_fails():
    render = _Render()
    runs = _RunsRepo()
    service = AutomationService(
        settings=_Settings(),
        whoop=_Whoop(),
        habits=_Habits(),
        render=render,
        lifecycle=_ExplodingLifecycle(),
        runs_repo=runs,
    )

    result = await service.run_nightly_pipeline(today=date(2026, 6, 1))

    assert runs.completed and not runs.failed
    assert result["remarkable"]["archive"]["status"] == "failed"
    assert result["remarkable"]["current"]["status"] == "failed"
    # Both renders survived.
    assert result["render"]["current"]["status"] == "completed"
    assert result["render"]["previous"]["status"] == "completed"
