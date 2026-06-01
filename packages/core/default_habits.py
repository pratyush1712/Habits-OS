"""Default HabitOS habit catalog for bootstrap/seed flows."""

from __future__ import annotations

from packages.core.models import Habit


def default_habits() -> list[Habit]:
    """Return the built-in habit definitions in stable display order.

    Sleep, recovery, and deep work are computed but not tracked as habits.
    Sleep and recovery are displayed as metrics on day subtitles and the tally page.
    Deep work has no evaluator and is removed entirely.
    """
    return [
        Habit(
            key="workout",
            label="Workout",
            short="W",
            kind="auto",
            enabled=True,
            sort_order=10,
            description="Exercise sessions from WHOOP or manual workout events.",
            event_types=["workout"],
            sources=["whoop", "manual"],
        ),
        Habit(
            key="meditation",
            label="Meditation",
            short="M",
            kind="auto",
            enabled=True,
            sort_order=30,
            description="Meditation sessions when meditation events exist.",
            event_types=["meditation"],
            sources=["muse", "apple_health", "manual"],
        ),
        Habit(
            key="journaling",
            label="Journaling",
            short="J",
            kind="auto",
            enabled=True,
            sort_order=40,
            description="Journal entries detected from Day One, with manual overrides honored.",
            event_types=["journal", "manual"],
            sources=["day_one", "manual"],
        ),
    ]
