"""Assemble the renderer-shaped month state from persisted projections.

This is the explicit "derive on read" path — no MonthHabitState snapshot is
ever persisted, per docs/persistence.md.
"""

from __future__ import annotations

from typing import Any

from packages.core.medication_plan import default_medication_groups
from packages.core.models import MedicationDayDose, MonthHabitState, SourceEvent
from packages.core.repositories import HabitEntriesRepo, HabitsRepo, SourceEventsRepo


class MonthStateService:
    def __init__(
        self,
        habits_repo: HabitsRepo,
        entries_repo: HabitEntriesRepo,
        events_repo: SourceEventsRepo,
    ) -> None:
        self.habits_repo = habits_repo
        self.entries_repo = entries_repo
        self.events_repo = events_repo

    async def get_state(self, month: str) -> MonthHabitState:
        habits = await self.habits_repo.list_active()
        entries = await self.entries_repo.list_by_month(month)
        events = await self.events_repo.list_by_month(month)
        return MonthHabitState(
            month=month,
            habits=habits,
            entries=entries,
            medication_groups=default_medication_groups(),
            medication_days=_medication_days_from_events(events),
        )


def _medication_days_from_events(events: list[SourceEvent]) -> list[MedicationDayDose]:
    days: list[MedicationDayDose] = []
    for event in events:
        if event.event_type != "medication":
            continue
        metrics: dict[str, Any] = event.metrics or event.raw_payload
        med_key = metrics.get("med_key")
        if not isinstance(med_key, str) or not med_key:
            continue
        taken = _coerce_nonnegative_int(metrics.get("taken_count", metrics.get("taken", 0)))
        total_value = metrics.get("scheduled_count", metrics.get("total_count", metrics.get("total")))
        total = _coerce_nonnegative_int(total_value) if total_value is not None else None
        days.append(
            MedicationDayDose(
                date=event.local_date,
                med_key=med_key,
                taken=taken,
                total=total,
            )
        )
    days.sort(key=lambda dose: (dose.date, dose.med_key))
    return days


def _coerce_nonnegative_int(value: Any) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return 0
    return max(coerced, 0)
