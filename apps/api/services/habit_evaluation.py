"""Run the rule engine for a month and persist the resulting HabitEntries."""

from __future__ import annotations

from typing import TypedDict

from packages.core.config import DEFAULT_RULES, HabitRuleConfig
from packages.core.repositories import (
    HabitEntriesRepo,
    HabitsRepo,
    ManualOverridesRepo,
    SourceEventsRepo,
)
from packages.core.rules import evaluate_month


class RecomputeResult(TypedDict):
    month: str
    habits: int
    events: int
    overrides: int
    entries_deleted: int
    entries_written: int
    warning: str | None


class HabitEvaluationService:
    def __init__(
        self,
        events_repo: SourceEventsRepo,
        overrides_repo: ManualOverridesRepo,
        habits_repo: HabitsRepo,
        entries_repo: HabitEntriesRepo,
        config: HabitRuleConfig = DEFAULT_RULES,
    ) -> None:
        self.events_repo = events_repo
        self.overrides_repo = overrides_repo
        self.habits_repo = habits_repo
        self.entries_repo = entries_repo
        self.config = config

    async def recompute(self, month: str) -> RecomputeResult:
        habits = await self.habits_repo.list_active()
        events = await self.events_repo.list_by_month(month)
        overrides = await self.overrides_repo.list_by_month(month)

        if not habits:
            return {
                "month": month,
                "habits": 0,
                "events": len(events),
                "overrides": len(overrides),
                "entries_deleted": 0,
                "entries_written": 0,
                "warning": (
                    "No active habits found. Seed defaults via POST /habits/seed-defaults "
                    "or enable at least one habit before recomputing."
                ),
            }

        state = evaluate_month(month, habits, events, overrides, self.config)

        deleted = await self.entries_repo.delete_month(month)
        written = await self.entries_repo.upsert_many(state.entries)

        return {
            "month": month,
            "habits": len(habits),
            "events": len(events),
            "overrides": len(overrides),
            "entries_deleted": deleted,
            "entries_written": written,
            "warning": None,
        }
