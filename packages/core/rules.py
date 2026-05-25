"""Pure habit rule engine.

Inputs: source events + manual overrides + rule config.
Outputs: HabitEntry per habit per date.

No I/O, no time-of-day, no global state. Every function is deterministic
and safe to call in tests.
"""

from __future__ import annotations

import calendar as _cal
from collections import defaultdict
from datetime import date
from typing import Callable, Iterable

from packages.core.config import HabitRuleConfig, DEFAULT_RULES
from packages.core.models import (
    Habit,
    HabitEntry,
    HabitOverride,
    HabitStatus,
    MonthHabitState,
    SourceEvent,
)


# ---------------------------------------------------------------------------
# Per-habit evaluators. Each takes the events for *one* day and the rule
# config, and returns either a HabitEntry or None (no entry → renders blank).
# ---------------------------------------------------------------------------


def evaluate_workout(
    day: date,
    events: list[SourceEvent],
    config: HabitRuleConfig = DEFAULT_RULES,
) -> HabitEntry | None:
    workouts = [e for e in events if e.event_type == "workout"]
    if not workouts:
        return None
    total = sum((e.duration_minutes or 0.0) for e in workouts)
    rule = config.workout
    if total >= rule.checked_min_minutes:
        status: HabitStatus = "checked"
    elif total >= rule.partial_min_minutes:
        status = "partial"
    else:
        # Below the partial threshold there's data but it's below what we'd call
        # "a workout." Stay silent rather than crowd the dashboard with noise.
        return None
    return HabitEntry(
        date=day,
        habit_key="workout",
        status=status,
        source=workouts[0].source,
        summary=_workout_summary(workouts),
        description=_join_descriptions(workouts),
        linked_source_event_ids=[e.id for e in workouts],
        explanation=(
            f"{_fmt_min(total)} workout "
            f"(checked >= {_fmt_min(rule.checked_min_minutes)}, "
            f"partial >= {_fmt_min(rule.partial_min_minutes)})"
        ),
    )


def evaluate_meditation(
    day: date,
    events: list[SourceEvent],
    config: HabitRuleConfig = DEFAULT_RULES,
) -> HabitEntry | None:
    sessions = [e for e in events if e.event_type == "meditation"]
    if not sessions:
        return None
    total = sum((e.duration_minutes or 0.0) for e in sessions)
    rule = config.meditation
    if total >= rule.checked_min_minutes:
        status: HabitStatus = "checked"
    elif total >= rule.partial_min_minutes:
        status = "partial"
    else:
        return None
    return HabitEntry(
        date=day,
        habit_key="meditation",
        status=status,
        source=sessions[0].source,
        summary=_meditation_summary(sessions),
        description=_join_descriptions(sessions),
        linked_source_event_ids=[e.id for e in sessions],
        explanation=(
            f"{_fmt_min(total)} meditation "
            f"(checked >= {_fmt_min(rule.checked_min_minutes)}, "
            f"partial >= {_fmt_min(rule.partial_min_minutes)})"
        ),
    )


def evaluate_sleep(
    day: date,
    events: list[SourceEvent],
    config: HabitRuleConfig = DEFAULT_RULES,
) -> HabitEntry | None:
    sleeps = [e for e in events if e.event_type == "sleep"]
    if not sleeps:
        return None
    # If multiple sleep records cover this date (e.g. a nap + the main sleep),
    # sum them. Real WHOOP data tends to send one main sleep per day, but the
    # rule should not break if a nap shows up.
    total_minutes = sum((e.duration_minutes or 0.0) for e in sleeps)
    target_minutes = config.sleep.target_hours * 60.0
    status: HabitStatus = "checked" if total_minutes >= target_minutes else "warning"

    # Pick the longest sleep as the "main" event for summary purposes.
    main = max(sleeps, key=lambda e: e.duration_minutes or 0.0)
    summary = _sleep_summary(total_minutes, main)
    return HabitEntry(
        date=day,
        habit_key="sleep",
        status=status,
        source=main.source,
        summary=summary,
        description=_join_descriptions(sleeps),
        linked_source_event_ids=[e.id for e in sleeps],
        explanation=(
            f"{total_minutes / 60:.1f}h sleep "
            f"(target {config.sleep.target_hours}h)"
        ),
    )


def evaluate_recovery(
    day: date,
    events: list[SourceEvent],
    config: HabitRuleConfig = DEFAULT_RULES,
) -> HabitEntry | None:
    recoveries = [e for e in events if e.event_type == "recovery"]
    scored = [
        e
        for e in recoveries
        if e.metrics.get("score_state") == "SCORED"
        and e.metrics.get("user_calibrating") is not True
        and e.metrics.get("recovery_score") is not None
    ]
    if not scored:
        return None

    # Multiple recovery records for one date should be rare; use the latest
    # normalized record so update/reconciliation semantics stay intuitive.
    latest = max(scored, key=lambda e: e.start_time_utc)
    score = int(latest.metrics["recovery_score"])
    status: HabitStatus = (
        "checked" if score >= config.recovery.checked_min_score else "warning"
    )
    return HabitEntry(
        date=day,
        habit_key="recovery",
        status=status,
        source=latest.source,
        summary=f"{score}% recovery",
        description=latest.description,
        linked_source_event_ids=[latest.id],
        explanation=(
            f"Recovery score {score}% "
            f"(checked >= {config.recovery.checked_min_score}%)"
        ),
    )


def evaluate_journaling(
    day: date,
    events: list[SourceEvent],
    config: HabitRuleConfig = DEFAULT_RULES,
) -> HabitEntry | None:
    journal_events = [e for e in events if e.event_type == "journal"]
    if not journal_events:
        return None
    entry_count = sum(int(e.metrics.get("entry_count", 1)) for e in journal_events)
    rule = config.journaling
    if entry_count < rule.checked_min_entries:
        return None
    return HabitEntry(
        date=day,
        habit_key="journaling",
        status="checked",
        source=journal_events[0].source,
        summary=_journal_summary(entry_count),
        description="",
        linked_source_event_ids=[e.id for e in journal_events],
        explanation=(
            f"{entry_count} journal entr{'y' if entry_count == 1 else 'ies'} "
            f"(checked >= {rule.checked_min_entries})"
        ),
    )


EVALUATORS: dict[str, Callable[[date, list[SourceEvent], HabitRuleConfig], HabitEntry | None]] = {
    "workout": evaluate_workout,
    "meditation": evaluate_meditation,
    "sleep": evaluate_sleep,
    "recovery": evaluate_recovery,
    "journaling": evaluate_journaling,
}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def evaluate_day(
    day: date,
    habit: Habit,
    events: list[SourceEvent],
    override: HabitOverride | None,
    config: HabitRuleConfig = DEFAULT_RULES,
) -> HabitEntry | None:
    """Resolve one habit on one date. Override always wins."""
    if override is not None:
        return _entry_from_override(habit, override)
    if habit.kind == "manual":
        return None
    evaluator = EVALUATORS.get(habit.key)
    if evaluator is None:
        # Habit declared as auto but no evaluator implemented — silently no entry.
        return None
    return evaluator(day, events, config)


def evaluate_month(
    month: str,
    habits: list[Habit],
    events: Iterable[SourceEvent],
    overrides: Iterable[HabitOverride],
    config: HabitRuleConfig = DEFAULT_RULES,
) -> MonthHabitState:
    """End-to-end: build a MonthHabitState from raw events and overrides."""
    year, month_num = (int(x) for x in month.split("-"))

    events_by_date: dict[date, list[SourceEvent]] = defaultdict(list)
    for e in events:
        if e.local_date.year == year and e.local_date.month == month_num:
            events_by_date[e.local_date].append(e)

    overrides_by_key: dict[tuple[date, str], HabitOverride] = {}
    for o in overrides:
        if o.date.year != year or o.date.month != month_num:
            continue
        key = (o.date, o.habit_key)
        if key in overrides_by_key:
            raise ValueError(
                f"Duplicate override for habit {o.habit_key!r} on {o.date.isoformat()}"
            )
        overrides_by_key[key] = o

    last_day = _cal.monthrange(year, month_num)[1]
    all_dates = [date(year, month_num, d) for d in range(1, last_day + 1)]

    entries: list[HabitEntry] = []
    for habit in habits:
        for day in all_dates:
            override = overrides_by_key.get((day, habit.key))
            day_events = events_by_date.get(day, [])
            entry = evaluate_day(day, habit, day_events, override, config)
            if entry is not None:
                entries.append(entry)

    entries.sort(key=lambda e: (e.date, e.habit_key))
    return MonthHabitState(month=month, habits=list(habits), entries=entries)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry_from_override(habit: Habit, o: HabitOverride) -> HabitEntry:
    return HabitEntry(
        date=o.date,
        habit_key=habit.key,
        status=o.status,
        source=o.source,
        summary=o.summary,
        description=o.description,
        confidence=1.0,
        explanation="manual override",
        manually_overridden=True,
    )


def _fmt_min(m: float) -> str:
    if m == int(m):
        return f"{int(m)}m"
    return f"{m:.1f}m"


def _join_descriptions(events: list[SourceEvent]) -> str:
    parts = [e.description for e in events if e.description]
    return " · ".join(parts)


def _workout_summary(events: list[SourceEvent]) -> str:
    if len(events) == 1:
        e = events[0]
        title = e.title or "Workout"
        return f"{_fmt_min(e.duration_minutes or 0.0)} {title}"
    total = sum((e.duration_minutes or 0.0) for e in events)
    return f"{_fmt_min(total)} total · {len(events)} sessions"


def _meditation_summary(events: list[SourceEvent]) -> str:
    if len(events) == 1:
        e = events[0]
        title = e.title or "Session"
        return f"{_fmt_min(e.duration_minutes or 0.0)} {title}"
    total = sum((e.duration_minutes or 0.0) for e in events)
    return f"{_fmt_min(total)} total · {len(events)} sessions"


def _journal_summary(entry_count: int) -> str:
    noun = "entry" if entry_count == 1 else "entries"
    return f"{entry_count} {noun}"


def _sleep_summary(total_minutes: float, main: SourceEvent) -> str:
    hours = int(total_minutes // 60)
    mins = int(round(total_minutes - hours * 60))
    parts = [f"{hours}h{mins:02d}m"]
    eff = main.metrics.get("efficiency_pct")
    if eff is not None:
        parts.append(f"{eff}%")
    return " · ".join(parts)
