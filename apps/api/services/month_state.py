"""Assemble a renderer-shaped MonthHabitState from the stored habit_entries.

This is the explicit "derive on read" path — no MonthHabitState snapshot is
ever persisted, per docs/persistence.md.
"""

from __future__ import annotations

from packages.core.models import MonthHabitState
from packages.core.repositories import HabitEntriesRepo, HabitsRepo


class MonthStateService:
    def __init__(self, habits_repo: HabitsRepo, entries_repo: HabitEntriesRepo) -> None:
        self.habits_repo = habits_repo
        self.entries_repo = entries_repo

    async def get_state(self, month: str) -> MonthHabitState:
        habits = await self.habits_repo.list_active()
        return await self.entries_repo.get_state(month, habits)
