"""APScheduler wiring for the HabitOS nightly pipeline."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


def build_scheduler(
    *,
    settings,
    run_job,
    scheduler_factory=AsyncIOScheduler,
):
    """Create and start the nightly scheduler when enabled."""

    if not settings.scheduler_enabled:
        return None

    scheduler = scheduler_factory(timezone=settings.habitos_timezone)
    scheduler.add_job(
        run_job,
        CronTrigger(
            hour=settings.nightly_run_hour,
            minute=settings.nightly_run_minute,
            timezone=settings.habitos_timezone,
        ),
        id="habitos-nightly",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
