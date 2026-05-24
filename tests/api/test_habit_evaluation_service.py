from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from apps.api.services.habit_evaluation import HabitEvaluationService
from packages.core.models import Habit, SourceEvent


class _EventsRepo:
    async def list_by_month(self, month: str):
        assert month == "2026-05"
        return [
            SourceEvent(
                id="whoop:w-1",
                source="whoop",
                source_event_id="w-1",
                event_type="workout",
                start_time_utc=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
                end_time_utc=datetime(2026, 5, 1, 12, 30, tzinfo=timezone.utc),
                local_date=date(2026, 5, 1),
            )
        ]


class _OverridesRepo:
    async def list_by_month(self, month: str):
        assert month == "2026-05"
        return []


class _HabitsRepoEmpty:
    async def list_active(self):
        return []


class _HabitsRepoActive:
    async def list_active(self):
        return [Habit(key="workout", label="Workout", short="W", kind="auto")]


class _EntriesRepo:
    def __init__(self) -> None:
        self.deleted = 0
        self.written = 0

    async def delete_month(self, month: str):
        assert month == "2026-05"
        self.deleted += 1
        return 0

    async def upsert_many(self, entries):
        self.written += len(entries)
        return len(entries)


@pytest.mark.asyncio
async def test_recompute_warns_when_no_active_habits():
    entries = _EntriesRepo()
    service = HabitEvaluationService(
        _EventsRepo(),
        _OverridesRepo(),
        _HabitsRepoEmpty(),
        entries,
    )
    result = await service.recompute("2026-05")
    assert result["entries_written"] == 0
    assert result["entries_deleted"] == 0
    assert result["warning"] is not None
    assert entries.deleted == 0
    assert entries.written == 0


@pytest.mark.asyncio
async def test_recompute_writes_entries_with_active_habits():
    entries = _EntriesRepo()
    service = HabitEvaluationService(
        _EventsRepo(),
        _OverridesRepo(),
        _HabitsRepoActive(),
        entries,
    )
    result = await service.recompute("2026-05")
    assert result["entries_written"] > 0
    assert result["warning"] is None
    assert entries.deleted == 1
