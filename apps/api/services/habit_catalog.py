"""Habit catalog seeding/listing service."""

from __future__ import annotations

from typing import TypedDict

from packages.core.default_habits import default_habits
from packages.core.models import Habit
from packages.core.repositories import HabitsRepo


class SeedDefaultsResult(TypedDict):
    seeded: int
    total_active: int
    retired: list[str]
    message: str


class HabitCatalogService:
    def __init__(self, habits_repo: HabitsRepo) -> None:
        self.habits_repo = habits_repo

    async def list_active(self) -> list[Habit]:
        return await self.habits_repo.list_active()

    async def ensure_default_habits(self) -> SeedDefaultsResult:
        total = await self.habits_repo.count_all()
        if total > 0:
            active = await self.habits_repo.list_active()
            return {
                "seeded": 0,
                "total_active": len(active),
                "retired": [],
                "message": "habit collection already initialized",
            }
        seeded = await self.habits_repo.upsert_many(default_habits())
        active = await self.habits_repo.list_active()
        return {
            "seeded": seeded,
            "total_active": len(active),
            "retired": [],
            "message": "seeded default habits",
        }

    async def seed_default_habits(self) -> SeedDefaultsResult:
        """Reconcile the stored catalog to the current defaults.

        Upserts every default habit (so flags like ``metric_only`` and new
        habits are applied to an already-initialized DB), then archives any
        active habit whose key is no longer in the defaults. This is what makes
        catalog edits — e.g. retiring ``deep_work`` or flipping ``sleep`` to
        metric-only — take effect on an existing deployment rather than only on
        a fresh one.
        """
        defaults = default_habits()
        default_keys = {h.key for h in defaults}

        seeded = await self.habits_repo.upsert_many(defaults)

        active_before = await self.habits_repo.list_active()
        retired = [h.key for h in active_before if h.key not in default_keys]
        for key in retired:
            await self.habits_repo.archive(key)

        active = await self.habits_repo.list_active()
        message = "upserted default habits"
        if retired:
            message += f"; archived {len(retired)} retired habit(s): {', '.join(sorted(retired))}"
        return {
            "seeded": seeded,
            "total_active": len(active),
            "retired": sorted(retired),
            "message": message,
        }
