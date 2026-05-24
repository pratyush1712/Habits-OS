"""Light round-trip checks for the domain models."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from packages.core.models import (
    Habit,
    HabitEntry,
    HabitOverride,
    MonthHabitState,
    SourceEvent,
)


def test_source_event_duration_minutes():
    e = SourceEvent(
        id="x:1",
        source="whoop",
        source_event_id="1",
        event_type="workout",
        start_time_utc=datetime(2026, 5, 1, 13, 0, tzinfo=timezone.utc),
        end_time_utc=datetime(2026, 5, 1, 13, 30, tzinfo=timezone.utc),
        local_date=date(2026, 5, 1),
    )
    assert e.duration_minutes == 30.0


def test_source_event_naive_datetime_coerced_to_utc():
    e = SourceEvent(
        id="x:1",
        source="whoop",
        source_event_id="1",
        event_type="workout",
        start_time_utc=datetime(2026, 5, 1, 13, 0),
        end_time_utc=datetime(2026, 5, 1, 13, 30),
        local_date=date(2026, 5, 1),
    )
    assert e.start_time_utc.tzinfo == timezone.utc


def test_month_state_validates_month_string():
    with pytest.raises(ValidationError):
        MonthHabitState(month="not-a-month", habits=[], entries=[])


def test_invalid_habit_status_rejected():
    with pytest.raises(ValidationError):
        HabitEntry(
            date=date(2026, 5, 1),
            habit_key="workout",
            status="spectacular",
            source="manual",
        )


def test_month_state_round_trip():
    state = MonthHabitState(
        month="2026-05",
        habits=[Habit(key="workout", label="Workout", short="W")],
        entries=[
            HabitEntry(
                date=date(2026, 5, 1),
                habit_key="workout",
                status="checked",
                source="whoop",
                summary="45m run",
            )
        ],
    )
    blob = state.model_dump_json()
    reloaded = MonthHabitState.model_validate_json(blob)
    assert reloaded.month == "2026-05"
    assert reloaded.entries[0].status == "checked"
    assert reloaded.entries[0].date == date(2026, 5, 1)


def test_override_default_source_is_manual():
    o = HabitOverride(date=date(2026, 5, 1), habit_key="journaling", status="checked")
    assert o.source == "manual"
