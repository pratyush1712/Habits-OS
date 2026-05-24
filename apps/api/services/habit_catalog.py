"""Habit catalog seeding/listing service."""

from __future__ import annotations

from typing import TypedDict

from packages.core.default_habits import default_habits
from packages.core.models import Habit
from packages.core.repositories import HabitsRepo


class SeedDefaultsResult(TypedDict):
    seeded: int
    total_active: int
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
                "message": "habit collection already initialized",
            }
        seeded = await self.habits_repo.upsert_many(default_habits())
        active = await self.habits_repo.list_active()
        return {
            "seeded": seeded,
            "total_active": len(active),
            "message": "seeded default habits",
        }

    async def seed_default_habits(self) -> SeedDefaultsResult:
        seeded = await self.habits_repo.upsert_many(default_habits())
        active = await self.habits_repo.list_active()
        return {
            "seeded": seeded,
            "total_active": len(active),
            "message": "upserted default habits",
        }
