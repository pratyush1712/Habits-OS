"""Integration tests for ManualOverridesRepo."""

from __future__ import annotations

from datetime import date

from packages.core.models import HabitOverride
from packages.core.repositories import ManualOverridesRepo


async def test_upsert_and_get(db):
    repo = ManualOverridesRepo(db)
    o = HabitOverride(date=date(2026, 5, 1), habit_key="journaling",
                      status="checked", summary="Morning pages")
    await repo.upsert(o)

    got = await repo.get(date(2026, 5, 1), "journaling")
    assert got is not None
    assert got.status == "checked"
    assert got.summary == "Morning pages"


async def test_upsert_replaces_existing(db):
    repo = ManualOverridesRepo(db)
    await repo.upsert(HabitOverride(date=date(2026, 5, 1), habit_key="workout", status="checked"))
    await repo.upsert(HabitOverride(date=date(2026, 5, 1), habit_key="workout", status="partial"))

    got = await repo.get(date(2026, 5, 1), "workout")
    assert got is not None and got.status == "partial"


async def test_list_by_month(db):
    repo = ManualOverridesRepo(db)
    await repo.upsert(HabitOverride(date=date(2026, 4, 30), habit_key="journaling", status="checked"))
    await repo.upsert(HabitOverride(date=date(2026, 5, 1), habit_key="journaling", status="checked"))
    await repo.upsert(HabitOverride(date=date(2026, 5, 15), habit_key="deep_work", status="checked"))
    await repo.upsert(HabitOverride(date=date(2026, 6, 1), habit_key="journaling", status="checked"))

    in_may = await repo.list_by_month("2026-05")
    assert [(o.date, o.habit_key) for o in in_may] == [
        (date(2026, 5, 1), "journaling"),
        (date(2026, 5, 15), "deep_work"),
    ]


async def test_delete(db):
    repo = ManualOverridesRepo(db)
    await repo.upsert(HabitOverride(date=date(2026, 5, 1), habit_key="workout", status="missed"))
    assert await repo.delete(date(2026, 5, 1), "workout") is True
    assert await repo.get(date(2026, 5, 1), "workout") is None
