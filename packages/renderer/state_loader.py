"""JSON → typed domain models.

Two input shapes are accepted:

1. **MonthHabitState** (preferred): the canonical renderer input. Produced by
   the rule engine or hand-authored.

2. **Legacy `sample_month.json`**: the original Milestone 1 shape with a
   `days` array of pre-evaluated entries. Loaded as a MonthHabitState whose
   entries are all marked `manually_overridden=True, source="manual"`.

A separate helper loads source events + overrides for the rule-engine path.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from packages.core.models import (
    Habit,
    HabitEntry,
    HabitOverride,
    MonthHabitState,
    SourceEvent,
)


def load_month_state(path: Path | str) -> MonthHabitState:
    raw = json.loads(Path(path).read_text())
    if "entries" in raw:
        return MonthHabitState.model_validate(raw)
    if "days" in raw:
        return _from_legacy(raw)
    raise ValueError(
        f"Unrecognised month state shape in {path}: expected 'entries' or 'days' key."
    )


def load_events_input(path: Path | str) -> tuple[str, list[Habit], list[SourceEvent], list[HabitOverride]]:
    """Load an events-style input file.

    Expected shape:
        {
          "month": "YYYY-MM",
          "habits": [Habit, ...],
          "source_events": [SourceEvent, ...],
          "manual_overrides": [HabitOverride, ...]   # optional
        }
    """
    raw = json.loads(Path(path).read_text())
    month = raw["month"]
    habits = [Habit.model_validate(h) for h in raw["habits"]]
    events = [SourceEvent.model_validate(e) for e in raw.get("source_events", [])]
    overrides = [HabitOverride.model_validate(o) for o in raw.get("manual_overrides", [])]
    return month, habits, events, overrides


def _from_legacy(raw: dict[str, Any]) -> MonthHabitState:
    habits = [Habit.model_validate({**h, "kind": h.get("kind", "auto")}) for h in raw["habits"]]
    medication_groups = raw.get("medication_groups", [])
    medication_days = raw.get("medication_days", [])
    entries: list[HabitEntry] = []
    for day in raw.get("days", []):
        d = date.fromisoformat(day["date"])
        for e in day.get("entries", []):
            entries.append(
                HabitEntry(
                    date=d,
                    habit_key=e["habit_key"],
                    status=e["status"],
                    source="manual",
                    summary=e.get("summary", ""),
                    description=e.get("description", ""),
                    explanation="loaded from legacy sample_month.json",
                    manually_overridden=True,
                )
            )
    entries.sort(key=lambda e: (e.date, e.habit_key))
    return MonthHabitState(
        month=raw["month"],
        habits=habits,
        entries=entries,
        medication_groups=medication_groups,
        medication_days=medication_days,
    )
