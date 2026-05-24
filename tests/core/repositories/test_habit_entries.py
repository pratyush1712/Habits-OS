"""Integration tests for HabitEntriesRepo."""

from __future__ import annotations

from datetime import date

from packages.core.models import Habit, HabitEntry
from packages.core.repositories import HabitEntriesRepo


def _entry(day: date, habit: str, status: str = "checked", source: str = "whoop"):
    return HabitEntry(date=day, habit_key=habit, status=status, source=source,
                     summary=f"{habit} on {day.isoformat()}")


async def test_upsert_many_round_trip(db):
    repo = HabitEntriesRepo(db)
    entries = [
        _entry(date(2026, 5, 1), "workout"),
        _entry(date(2026, 5, 1), "sleep"),
        _entry(date(2026, 5, 2), "workout"),
    ]
    n = await repo.upsert_many(entries)
    assert n == 3

    in_may = await repo.list_by_month("2026-05")
    keys = [(e.date, e.habit_key) for e in in_may]
    assert keys == sorted(keys)
    assert len(in_may) == 3


async def test_upsert_replaces_on_same_natural_key(db):
    repo = HabitEntriesRepo(db)
    await repo.upsert(_entry(date(2026, 5, 1), "workout", status="partial"))
    await repo.upsert(_entry(date(2026, 5, 1), "workout", status="checked"))

    got = await repo.get(date(2026, 5, 1), "workout")
    assert got is not None and got.status == "checked"

    all_in_may = await repo.list_by_month("2026-05")
    assert len(all_in_may) == 1


async def test_get_state_assembles_month_habit_state(db):
    repo = HabitEntriesRepo(db)
    await repo.upsert_many([
        _entry(date(2026, 5, 1), "workout"),
        _entry(date(2026, 5, 1), "sleep"),
    ])
    habits = [
        Habit(key="workout", label="Workout", short="W"),
        Habit(key="sleep", label="Sleep", short="Z"),
    ]
    state = await repo.get_state("2026-05", habits)
    assert state.month == "2026-05"
    assert len(state.habits) == 2
    assert len(state.entries) == 2


async def test_delete_month(db):
    repo = HabitEntriesRepo(db)
    await repo.upsert_many([
        _entry(date(2026, 4, 30), "workout"),
        _entry(date(2026, 5, 1), "workout"),
        _entry(date(2026, 5, 15), "workout"),
        _entry(date(2026, 6, 1), "workout"),
    ])
    deleted = await repo.delete_month("2026-05")
    assert deleted == 2

    remaining = await repo.list_by_month("2026-04")
    assert len(remaining) == 1
    remaining = await repo.list_by_month("2026-06")
    assert len(remaining) == 1
    remaining = await repo.list_by_month("2026-05")
    assert remaining == []
