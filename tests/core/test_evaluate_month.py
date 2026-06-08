"""End-to-end: events + overrides → MonthHabitState."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from packages.core.models import Habit, HabitOverride, SourceEvent
from packages.core.rules import evaluate_month
from packages.renderer.state_loader import load_events_input


HABITS = [
    Habit(key="workout", label="Workout", short="W", kind="auto"),
    Habit(key="sleep", label="Sleep", short="Z", kind="auto"),
    Habit(key="medication", label="Medication", short="Rx", kind="auto"),
    Habit(key="meditation", label="Meditation", short="M", kind="auto"),
    Habit(key="journaling", label="Journaling", short="J", kind="manual"),
    Habit(key="deep_work", label="Deep work", short="D", kind="manual"),
]


def _ev(event_type, day, minutes, **kw):
    start = datetime(day.year, day.month, day.day, 13, 0, tzinfo=timezone.utc)
    return SourceEvent(
        id=kw.pop("id", f"x:{event_type}:{day.isoformat()}"),
        source=kw.pop("source", "whoop"),
        source_event_id=kw.pop("source_event_id", f"{event_type}-{day.isoformat()}"),
        event_type=event_type,
        start_time_utc=start,
        end_time_utc=start + timedelta(minutes=minutes),
        local_date=day,
        **kw,
    )


def test_only_events_in_target_month_count():
    """Events in adjacent months must be ignored."""
    events = [
        _ev("workout", date(2026, 4, 30), 45),
        _ev("workout", date(2026, 5, 1), 45),
        _ev("workout", date(2026, 6, 1), 45),
    ]
    state = evaluate_month("2026-05", HABITS, events, [])
    workout_entries = [e for e in state.entries if e.habit_key == "workout"]
    assert len(workout_entries) == 1
    assert workout_entries[0].date == date(2026, 5, 1)


def test_overrides_in_other_months_ignored():
    overrides = [
        HabitOverride(date=date(2026, 4, 30), habit_key="journaling", status="checked"),
        HabitOverride(date=date(2026, 5, 1), habit_key="journaling", status="checked"),
    ]
    state = evaluate_month("2026-05", HABITS, [], overrides)
    journaling = [e for e in state.entries if e.habit_key == "journaling"]
    assert len(journaling) == 1


def test_duplicate_override_raises():
    overrides = [
        HabitOverride(date=date(2026, 5, 1), habit_key="journaling", status="checked"),
        HabitOverride(date=date(2026, 5, 1), habit_key="journaling", status="partial"),
    ]
    with pytest.raises(ValueError):
        evaluate_month("2026-05", HABITS, [], overrides)


def test_entries_sorted_by_date_then_habit():
    events = [
        _ev("workout", date(2026, 5, 3), 30),
        _ev("workout", date(2026, 5, 1), 30),
    ]
    overrides = [
        HabitOverride(date=date(2026, 5, 1), habit_key="journaling", status="checked"),
    ]
    state = evaluate_month("2026-05", HABITS, events, overrides)
    keys = [(e.date, e.habit_key) for e in state.entries]
    assert keys == sorted(keys)


def test_full_sample_events_file_loads_and_evaluates():
    """Pin Milestone 2 acceptance: the committed sample produces a coherent state."""
    sample = Path(__file__).resolve().parents[2] / "data" / "sample_events.json"
    month, habits, events, overrides = load_events_input(sample)
    state = evaluate_month(month, habits, events, overrides)

    by_key = {(e.date.isoformat(), e.habit_key): e for e in state.entries}

    # May 1: all three auto habits should be checked.
    assert by_key[("2026-05-01", "workout")].status == "checked"
    assert by_key[("2026-05-01", "sleep")].status == "checked"
    assert by_key[("2026-05-01", "meditation")].status == "checked"

    # May 2: sleep is under target → warning. No workout event → no entry.
    assert by_key[("2026-05-02", "sleep")].status == "warning"
    assert ("2026-05-02", "workout") not in by_key

    # May 3: 12-minute workout → partial.
    assert by_key[("2026-05-03", "workout")].status == "partial"

    # May 4: 4-minute workout falls below partial → no entry.
    assert ("2026-05-04", "workout") not in by_key
    # 3-min meditation → partial.
    assert by_key[("2026-05-04", "meditation")].status == "partial"
    # Manual journaling override applied.
    j = by_key[("2026-05-04", "journaling")]
    assert j.status == "checked" and j.manually_overridden

    # May 5: two workouts summing to 28m → checked.
    assert by_key[("2026-05-05", "workout")].status == "checked"
    assert len(by_key[("2026-05-05", "workout")].linked_source_event_ids) == 2

    # May 7: workout override wins over the computed entry.
    w7 = by_key[("2026-05-07", "workout")]
    assert w7.status == "manual" and w7.manually_overridden
    assert "manually marked" in w7.summary

    # May 31: medication/supplement sample creates a partial aggregate entry.
    med = by_key[("2026-05-31", "medication")]
    assert med.status == "partial"
    assert med.summary == "7/11 scheduled doses"

    # May 31: manual-only journaling via override still appears.
    assert by_key[("2026-05-31", "journaling")].status == "manual"
