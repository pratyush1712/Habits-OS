"""Light round-trip checks for the domain models."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from packages.core.models import (
    AutomationRun,
    Habit,
    HabitEntry,
    HabitOverride,
    MedicationDayDose,
    MedicationGroup,
    MedicationItem,
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


def test_automation_run_round_trip():
    run = AutomationRun(
        run_type="nightly",
        status="running",
        dry_run=True,
        timezone="America/New_York",
        date="2026-06-01",
        window={"start": "2026-05-18", "end": "2026-06-01", "reconcile_days": 14},
        months={"current": "2026-06", "previous": "2026-05", "affected": ["2026-05", "2026-06"]},
        whoop_summary={"status": "pending"},
        habit_recompute_summary=[],
        render_summary={"current": {"status": "pending"}},
        remarkable_summary={"status": "pending"},
    )

    blob = run.model_dump_json()
    reloaded = AutomationRun.model_validate_json(blob)
    assert reloaded.run_type == "nightly"
    assert reloaded.window["reconcile_days"] == 14
    assert reloaded.months["affected"] == ["2026-05", "2026-06"]


def test_source_event_accepts_day_one_source_literal():
    e = SourceEvent(
        id="day_one:dayone:2026-05-01",
        source="day_one",
        source_event_id="dayone:2026-05-01",
        event_type="journal",
        start_time_utc=datetime(2026, 5, 1, 9, 30, tzinfo=timezone.utc),
        end_time_utc=datetime(2026, 5, 1, 22, 0, tzinfo=timezone.utc),
        local_date=date(2026, 5, 1),
        metrics={"entry_count": 2},
    )
    assert e.source == "day_one"
    assert e.event_type == "journal"


def test_automation_run_dayone_summary_defaults_and_round_trips():
    run = AutomationRun(
        run_type="nightly",
        status="running",
        dry_run=True,
        timezone="UTC",
        date="2026-06-01",
        window={"start": "2026-05-30", "end": "2026-06-01", "reconcile_days": 2},
        months={"current": "2026-06", "previous": "2026-05", "affected": ["2026-05", "2026-06"]},
        whoop_summary={},
        dayone_summary={"inserted": 1, "updated": 0, "skipped_reason": None},
        habit_recompute_summary=[],
        render_summary={},
        remarkable_summary={},
    )
    assert run.dayone_summary["inserted"] == 1
    reloaded = AutomationRun.model_validate_json(run.model_dump_json())
    assert reloaded.dayone_summary["skipped_reason"] is None


def test_automation_run_dayone_summary_optional_defaults_to_empty():
    run = AutomationRun(
        run_type="nightly",
        status="running",
        dry_run=True,
        timezone="UTC",
        date="2026-06-01",
        window={"start": "2026-05-30", "end": "2026-06-01", "reconcile_days": 2},
        months={"current": "2026-06", "previous": "2026-05", "affected": ["2026-05", "2026-06"]},
    )
    assert run.dayone_summary == {}


def test_automation_run_rejects_invalid_date_string():
    with pytest.raises(ValidationError):
        AutomationRun(
            run_type="manual",
            status="running",
            dry_run=True,
            timezone="UTC",
            date="2026/06/01",
            window={"start": "2026-05-18", "end": "2026-06-01", "reconcile_days": 14},
            months={"current": "2026-06", "previous": "2026-05", "affected": ["2026-05", "2026-06"]},
            whoop_summary={},
            habit_recompute_summary=[],
            render_summary={},
            remarkable_summary={},
        )



def test_source_event_accepts_medication_literal():
    e = SourceEvent(
        id="manual:med-2026-05-31-magnesium",
        source="manual",
        source_event_id="med-2026-05-31-magnesium",
        event_type="medication",
        start_time_utc=datetime(2026, 5, 31, 23, 0, tzinfo=timezone.utc),
        local_date=date(2026, 5, 31),
        metrics={"med_key": "magnesium", "taken_count": 1, "scheduled_count": 2},
    )
    assert e.event_type == "medication"


def test_month_state_accepts_medication_schedule_metadata():
    state = MonthHabitState(
        month="2026-05",
        habits=[],
        entries=[],
        medication_groups=[
            MedicationGroup(
                key="night",
                label="Night",
                meds=[MedicationItem(key="magnesium", label="Mg", short="Mg", dose="2 x 100mg", total=2)],
            )
        ],
        medication_days=[MedicationDayDose(date=date(2026, 5, 31), med_key="magnesium", taken=1, total=2)],
    )
    assert state.medication_groups[0].meds[0].key == "magnesium"
    assert state.medication_days[0].taken == 1
