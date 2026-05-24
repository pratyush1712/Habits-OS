"""Default HabitOS habit catalog for bootstrap/seed flows."""

from __future__ import annotations

from packages.core.models import Habit


def default_habits() -> list[Habit]:
    """Return the built-in habit definitions in stable display order."""
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
            key="sleep",
            label="Sleep",
            short="Z",
            kind="auto",
            enabled=True,
            sort_order=20,
            description="Nightly sleep duration from WHOOP sleep events.",
            event_types=["sleep"],
            sources=["whoop"],
        ),
        Habit(
            key="recovery",
            label="Recovery",
            short="R",
            kind="auto",
            enabled=True,
            sort_order=30,
            description="WHOOP recovery score status for each day.",
            event_types=["recovery"],
            sources=["whoop"],
        ),
        Habit(
            key="meditation",
            label="Meditation",
            short="M",
            kind="auto",
            enabled=True,
            sort_order=40,
            description="Meditation sessions when meditation events exist.",
            event_types=["meditation"],
            sources=["muse", "apple_health", "manual"],
        ),
        Habit(
            key="journaling",
            label="Journaling",
            short="J",
            kind="manual",
            enabled=True,
            sort_order=50,
            description="Manual journaling check-in for MVP.",
            event_types=["journal", "manual"],
            sources=["manual"],
        ),
        Habit(
            key="deep_work",
            label="Deep Work",
            short="D",
            kind="manual",
            enabled=True,
            sort_order=60,
            description="Manual deep-work check-in for MVP.",
            event_types=["deep_work", "manual"],
            sources=["manual"],
        ),
    ]
