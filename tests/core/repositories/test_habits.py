"""Integration tests for HabitsRepo."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.core.models import Habit
from packages.core.repositories import HabitsRepo


async def test_upsert_and_get(db):
    repo = HabitsRepo(db)
    await repo.upsert(Habit(key="workout", label="Workout", short="W"))
    got = await repo.get("workout")
    assert got is not None and got.label == "Workout"


async def test_upsert_preserves_archived_at_across_writes(db):
    repo = HabitsRepo(db)
    await repo.upsert(Habit(key="meditation", label="Meditation", short="M"))
    await repo.archive("meditation")

    # Re-upsert: archived_at must not be wiped.
    await repo.upsert(Habit(key="meditation", label="Meditation 2", short="M"))
    active = await repo.list_active()
    assert all(h.key != "meditation" for h in active)


async def test_list_active_excludes_archived(db):
    repo = HabitsRepo(db)
    await repo.upsert_many([
        Habit(key="workout", label="Workout", short="W"),
        Habit(key="sleep", label="Sleep", short="Z"),
        Habit(key="rituals", label="Rituals", short="R"),
    ])
    await repo.archive("rituals")

    active = await repo.list_active()
    assert {h.key for h in active} == {"workout", "sleep"}

    all_habits = await repo.list_all()
    assert {h.key for h in all_habits} == {"workout", "sleep", "rituals"}


async def test_upsert_many_round_trip(db):
    repo = HabitsRepo(db)
    n = await repo.upsert_many([
        Habit(key="a", label="A", short="A"),
        Habit(key="b", label="B", short="B"),
    ])
    assert n == 2
    assert len(await repo.list_active()) == 2


async def test_get_ignores_legacy_audit_fields(db):
    repo = HabitsRepo(db)
    await repo.coll.insert_one({
        "_id": "workout",
        "key": "workout",
        "label": "Workout",
        "short": "W",
        "archived_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    got = await repo.get("workout")

    assert got == Habit(key="workout", label="Workout", short="W")
