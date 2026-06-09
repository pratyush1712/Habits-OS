"""Default HabitOS habit catalog for bootstrap/seed flows."""

from __future__ import annotations

from packages.core.models import Habit


def default_habits() -> list[Habit]:
    """Return the built-in habit definitions in stable display order.

    Five habits are deliberate, user-controlled actions and render as cards in
    the grid and tally: ``workout``, ``medication``, ``protein_shake``,
    ``meditation``, and ``journaling``. ``protein_shake`` is logged manually
    from the iOS app or admin/web app (same flow as ``medication``, but tracked
    as its own habit and not part of the medication plan/tally).

    ``sleep`` and ``recovery`` are ``metric_only``: they are still computed and
    stored from WHOOP data (so the numbers stay visible next to each day's date
    and on the tally), but they are not checkboxes — they reflect the body's
    state, not something the user decides to "do". ``deep_work`` was removed
    entirely: there is no signal to evaluate it and the concept is too broad.

    Re-running the seed-defaults flow reconciles an existing catalog to this
    list, archiving any habit that no longer appears here (e.g. ``deep_work``).
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
            key="medication",
            label="Medication",
            short="Rx",
            kind="auto",
            enabled=True,
            sort_order=20,
            description="Medication and supplement dose logs from manual tracking events.",
            event_types=["medication"],
            sources=["manual", "medication"],
        ),
        Habit(
            key="protein_shake",
            label="Protein Shake",
            short="P",
            kind="auto",
            enabled=True,
            sort_order=25,
            description="Protein shake logs from manual tracking (app or web app).",
            event_types=["protein_shake"],
            sources=["manual"],
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
        Habit(
            key="sleep",
            label="Sleep",
            short="Z",
            kind="auto",
            enabled=True,
            metric_only=True,
            sort_order=50,
            description="Sleep duration/efficiency from WHOOP, shown as a metric (not a habit).",
            event_types=["sleep"],
            sources=["whoop"],
        ),
        Habit(
            key="recovery",
            label="Recovery",
            short="R",
            kind="auto",
            enabled=True,
            metric_only=True,
            sort_order=60,
            description="Recovery score from WHOOP, shown as a metric (not a habit).",
            event_types=["recovery"],
            sources=["whoop"],
        ),
    ]
