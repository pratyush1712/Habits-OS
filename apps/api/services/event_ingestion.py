"""Ingest source events + overrides + habit catalog from a JSON file."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from packages.core.repositories import (
    HabitsRepo,
    ManualOverridesRepo,
    SourceEventsRepo,
)
from packages.renderer.state_loader import load_events_input


class IngestionResult(TypedDict):
    month: str
    habits: int
    events: int
    overrides: int


class EventIngestionService:
    def __init__(
        self,
        events_repo: SourceEventsRepo,
        overrides_repo: ManualOverridesRepo,
        habits_repo: HabitsRepo,
    ) -> None:
        self.events_repo = events_repo
        self.overrides_repo = overrides_repo
        self.habits_repo = habits_repo

    async def import_from_file(self, path: Path) -> IngestionResult:
        month, habits, events, overrides = load_events_input(path)
        habits_n = await self.habits_repo.upsert_many(habits)
        events_n = await self.events_repo.upsert_many(events)
        overrides_n = 0
        for o in overrides:
            await self.overrides_repo.upsert(o)
            overrides_n += 1
        return {
            "month": month,
            "habits": habits_n,
            "events": events_n,
            "overrides": overrides_n,
        }
