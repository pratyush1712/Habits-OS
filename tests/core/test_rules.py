"""Boundary tests for the rule engine.

Every threshold-driven branch is exercised with one event just over and one
event just under the threshold. Override precedence and no-event behaviour
are covered explicitly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from packages.core.config import (
    HabitRuleConfig,
    JournalingRule,
    ProteinShakeRule,
    RecoveryRule,
    SleepRule,
)
from packages.core.models import Habit, HabitOverride, SourceEvent
from packages.core.rules import (
    evaluate_day,
    evaluate_journaling,
    evaluate_medication,
    evaluate_meditation,
    evaluate_protein_shake,
    evaluate_recovery,
    evaluate_sleep,
    evaluate_workout,
)

DAY = date(2026, 5, 1)


def _event(event_type, minutes, **kwargs):
    start = datetime(2026, 5, 1, 13, 0, tzinfo=timezone.utc)
    return SourceEvent(
        id=kwargs.pop("id", f"x:{event_type}-{minutes}"),
        source=kwargs.pop("source", "whoop"),
        source_event_id=kwargs.pop("source_event_id", f"{event_type}-{minutes}"),
        event_type=event_type,
        start_time_utc=start,
        end_time_utc=start + timedelta(minutes=minutes),
        local_date=DAY,
        **kwargs,
    )


# ---------- workout ----------


def test_workout_no_events_returns_none():
    assert evaluate_workout(DAY, []) is None


def test_workout_below_partial_threshold_returns_none():
    # 4 minutes is below the 5-minute partial threshold.
    assert evaluate_workout(DAY, [_event("workout", 4)]) is None


def test_workout_partial_boundary():
    entry = evaluate_workout(DAY, [_event("workout", 5)])
    assert entry is not None and entry.status == "partial"


def test_workout_partial_just_under_checked():
    entry = evaluate_workout(DAY, [_event("workout", 14)])
    assert entry is not None and entry.status == "partial"


def test_workout_checked_boundary():
    entry = evaluate_workout(DAY, [_event("workout", 15)])
    assert entry is not None and entry.status == "checked"


def test_workout_sums_multiple_events():
    # 8 + 8 = 16 → checked despite each individual event being under threshold.
    entry = evaluate_workout(DAY, [_event("workout", 8, id="a", source_event_id="a"),
                                   _event("workout", 8, id="b", source_event_id="b")])
    assert entry is not None and entry.status == "checked"
    assert len(entry.linked_source_event_ids) == 2


def test_workout_ignores_non_workout_events():
    entry = evaluate_workout(DAY, [_event("sleep", 480)])
    assert entry is None


# ---------- meditation ----------


def test_meditation_no_events_returns_none():
    assert evaluate_meditation(DAY, []) is None


def test_meditation_below_partial_returns_none():
    assert evaluate_meditation(DAY, [_event("meditation", 1)]) is None


def test_meditation_partial_boundary():
    entry = evaluate_meditation(DAY, [_event("meditation", 2)])
    assert entry is not None and entry.status == "partial"


def test_meditation_checked_boundary():
    entry = evaluate_meditation(DAY, [_event("meditation", 5)])
    assert entry is not None and entry.status == "checked"



# ---------- medication ----------


def _med_event(med_key, taken, scheduled, *, day=DAY, prn=False, label=None):
    start = datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc)
    return SourceEvent(
        id=f"manual:med:{day.isoformat()}:{med_key}",
        source="manual",
        source_event_id=f"med:{day.isoformat()}:{med_key}",
        event_type="medication",
        start_time_utc=start,
        local_date=day,
        title=label or med_key,
        metrics={
            "med_key": med_key,
            "med_label": label or med_key,
            "taken_count": taken,
            "scheduled_count": scheduled,
            "prn": prn,
        },
    )


def test_medication_no_events_returns_none():
    assert evaluate_medication(DAY, []) is None


def test_medication_checked_when_all_scheduled_doses_taken():
    entry = evaluate_medication(DAY, [
        _med_event("propranolol_morning", 1, 1),
        _med_event("magnesium", 2, 2),
    ])
    assert entry is not None
    assert entry.habit_key == "medication"
    assert entry.status == "checked"
    assert entry.summary == "3/3 scheduled doses"


def test_medication_partial_when_some_scheduled_doses_taken():
    entry = evaluate_medication(DAY, [
        _med_event("adderall_xr", 0, 1, label="Add 30"),
        _med_event("adderall_ir", 1, 1, label="Add 20"),
        _med_event("omega_3", 1, 3, label="O3"),
    ])
    assert entry is not None
    assert entry.status == "partial"
    assert entry.summary == "2/5 scheduled doses"
    assert "Add 30: 0/1" in entry.description


def test_medication_missed_when_observed_scheduled_day_has_zero_taken():
    entry = evaluate_medication(DAY, [_med_event("magnesium", 0, 2)])
    assert entry is not None
    assert entry.status == "missed"
    assert entry.summary == "0/2 scheduled doses"


def test_medication_prn_absence_does_not_create_entry():
    entry = evaluate_medication(DAY, [_med_event("hydroxyzine", 0, 0, prn=True)])
    assert entry is None


def test_medication_prn_taken_is_informational_checked_entry():
    entry = evaluate_medication(DAY, [_med_event("hydroxyzine", 1, 0, prn=True)])
    assert entry is not None
    assert entry.status == "checked"
    assert entry.summary == "1 PRN dose"
    assert "absence of PRN" in entry.explanation

# ---------- protein shake ----------


def _shake_event(count, *, day=DAY):
    start = datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc)
    return SourceEvent(
        id=f"manual:protein-shake-{day.isoformat()}",
        source="manual",
        source_event_id=f"protein-shake-{day.isoformat()}",
        event_type="protein_shake",
        start_time_utc=start,
        local_date=day,
        title=f"{count} protein shakes",
        metrics={"count": count},
    )


def test_protein_shake_no_events_returns_none():
    assert evaluate_protein_shake(DAY, []) is None


def test_protein_shake_ignores_non_shake_events():
    assert evaluate_protein_shake(DAY, [_event("workout", 30)]) is None


def test_protein_shake_single_is_checked_singular_summary():
    entry = evaluate_protein_shake(DAY, [_shake_event(1)])
    assert entry is not None
    assert entry.habit_key == "protein_shake"
    assert entry.status == "checked"
    assert entry.source == "manual"
    assert entry.summary == "1 shake"


def test_protein_shake_multiple_is_checked_plural_summary():
    entry = evaluate_protein_shake(DAY, [_shake_event(2)])
    assert entry is not None
    assert entry.status == "checked"
    assert entry.summary == "2 shakes"


def test_protein_shake_zero_count_leaves_day_blank():
    assert evaluate_protein_shake(DAY, [_shake_event(0)]) is None


def test_protein_shake_threshold_can_be_raised():
    cfg = HabitRuleConfig(protein_shake=ProteinShakeRule(checked_min_count=2))
    assert evaluate_protein_shake(DAY, [_shake_event(1)], cfg) is None
    entry = evaluate_protein_shake(DAY, [_shake_event(2)], cfg)
    assert entry is not None
    assert entry.status == "checked"


# ---------- sleep ----------


def test_sleep_no_events_returns_none():
    assert evaluate_sleep(DAY, []) is None


def test_sleep_at_target_is_checked():
    # default target 7h
    entry = evaluate_sleep(DAY, [_event("sleep", 7 * 60)])
    assert entry is not None and entry.status == "checked"


def test_sleep_under_target_is_warning():
    entry = evaluate_sleep(DAY, [_event("sleep", 6 * 60 + 30)])
    assert entry is not None and entry.status == "warning"


def test_sleep_custom_target():
    cfg = HabitRuleConfig(sleep=SleepRule(target_hours=8.0))
    entry = evaluate_sleep(DAY, [_event("sleep", 7 * 60 + 30)], cfg)
    assert entry is not None and entry.status == "warning"


def test_sleep_summary_uses_metric_efficiency():
    e = _event("sleep", 7 * 60 + 45, metrics={"efficiency_pct": 89})
    entry = evaluate_sleep(DAY, [e])
    assert entry is not None
    assert "89%" in entry.summary


# ---------- evaluate_day: overrides + manual habits ----------


WORKOUT_HABIT = Habit(key="workout", label="Workout", short="W", kind="auto")
JOURNALING_HABIT = Habit(key="journaling", label="Journaling", short="J", kind="manual")


def test_override_wins_over_computed_entry():
    override = HabitOverride(date=DAY, habit_key="workout", status="manual",
                             summary="manually marked")
    entry = evaluate_day(DAY, WORKOUT_HABIT, [_event("workout", 45)], override)
    assert entry is not None
    assert entry.status == "manual"
    assert entry.manually_overridden is True
    assert entry.summary == "manually marked"


def test_manual_habit_with_no_override_returns_none():
    entry = evaluate_day(DAY, JOURNALING_HABIT, [], None)
    assert entry is None


def test_manual_habit_with_override_is_emitted():
    override = HabitOverride(date=DAY, habit_key="journaling", status="checked",
                             summary="Morning pages")
    entry = evaluate_day(DAY, JOURNALING_HABIT, [], override)
    assert entry is not None
    assert entry.status == "checked"
    assert entry.manually_overridden is True


def test_auto_habit_with_no_events_returns_none():
    # No "missed" auto-marking — our chosen rule.
    entry = evaluate_day(DAY, WORKOUT_HABIT, [], None)
    assert entry is None


def test_unknown_auto_habit_returns_none():
    """Auto habits without an evaluator should silently produce no entry."""
    unknown = Habit(key="hydration", label="Hydration", short="H", kind="auto")
    entry = evaluate_day(DAY, unknown, [_event("workout", 30)], None)
    assert entry is None

# ---------- recovery ----------


def _recovery_event(score, **kwargs):
    return _event(
        "recovery",
        0,
        id=kwargs.pop("id", f"x:recovery-{score}"),
        source_event_id=kwargs.pop("source_event_id", f"recovery-{score}"),
        metrics={
            "score_state": kwargs.pop("score_state", "SCORED"),
            "user_calibrating": kwargs.pop("user_calibrating", False),
            "recovery_score": score,
        },
        **kwargs,
    )


def test_recovery_no_events_returns_none():
    assert evaluate_recovery(DAY, []) is None


def test_recovery_checked_boundary():
    entry = evaluate_recovery(DAY, [_recovery_event(67)])
    assert entry is not None
    assert entry.status == "checked"
    assert entry.habit_key == "recovery"


def test_recovery_under_threshold_is_warning():
    entry = evaluate_recovery(DAY, [_recovery_event(44)])
    assert entry is not None
    assert entry.status == "warning"


def test_recovery_ignores_unscored_or_calibrating():
    assert evaluate_recovery(DAY, [_recovery_event(80, score_state="PENDING_SCORE")]) is None
    assert evaluate_recovery(DAY, [_recovery_event(80, user_calibrating=True)]) is None


def test_recovery_custom_threshold():
    cfg = HabitRuleConfig(recovery=RecoveryRule(checked_min_score=80))
    entry = evaluate_recovery(DAY, [_recovery_event(77)], cfg)
    assert entry is not None
    assert entry.status == "warning"


# ---------- journaling ----------


def _journal_event(*, day=DAY, entry_count=1, source="day_one", source_event_id=None):
    start = datetime(day.year, day.month, day.day, 9, 0, tzinfo=timezone.utc)
    sid = source_event_id or f"dayone:{day.isoformat()}"
    return SourceEvent(
        id=f"day_one:{sid}",
        source=source,
        source_event_id=sid,
        event_type="journal",
        start_time_utc=start,
        end_time_utc=start + timedelta(hours=1),
        local_date=day,
        title=f"{entry_count} journal entries",
        metrics={"entry_count": entry_count, "journal_names": ["Personal"], "journal_ids": ["j1"]},
    )


def test_journaling_no_events_returns_none():
    assert evaluate_journaling(DAY, []) is None


def test_journaling_ignores_non_journal_events():
    assert evaluate_journaling(DAY, [_event("workout", 30)]) is None


def test_journaling_single_entry_is_checked():
    entry = evaluate_journaling(DAY, [_journal_event(entry_count=1)])
    assert entry is not None
    assert entry.habit_key == "journaling"
    assert entry.status == "checked"
    assert entry.source == "day_one"
    assert entry.summary == "1 entry"
    assert entry.description == ""


def test_journaling_multiple_entries_is_checked_with_plural_summary():
    entry = evaluate_journaling(DAY, [_journal_event(entry_count=3)])
    assert entry is not None
    assert entry.status == "checked"
    assert entry.summary == "3 entries"


def test_journaling_threshold_can_be_raised():
    cfg = HabitRuleConfig(journaling=JournalingRule(checked_min_entries=2))
    assert evaluate_journaling(DAY, [_journal_event(entry_count=1)], cfg) is None
    entry = evaluate_journaling(DAY, [_journal_event(entry_count=2)], cfg)
    assert entry is not None
    assert entry.status == "checked"


def test_journaling_manual_override_wins_over_day_one_data():
    habit = Habit(
        key="journaling",
        label="Journaling",
        short="J",
        kind="auto",
        sources=["day_one", "manual"],
        event_types=["journal", "manual"],
    )
    override = HabitOverride(
        date=DAY, habit_key="journaling", status="missed", summary="not today"
    )
    entry = evaluate_day(DAY, habit, [_journal_event(entry_count=5)], override)
    assert entry is not None
    assert entry.status == "missed"
    assert entry.manually_overridden is True
    assert entry.source == "manual"
