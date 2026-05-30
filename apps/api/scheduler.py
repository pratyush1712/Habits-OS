"""APScheduler wiring for the HabitOS nightly pipeline."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)

# How late the server can start and still fire a missed job.
# 3600 s = 1 hour — covers sleep/wake cycles that delay the 3 AM cron.
_MISFIRE_GRACE_SECONDS = 3600


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
        misfire_grace_time=_MISFIRE_GRACE_SECONDS,
        coalesce=True,
    )
    scheduler.start()
    return scheduler


def maybe_schedule_catchup(*, settings, run_job, runs_repo) -> None:
    """Fire a catch-up run at startup if today's nightly job was missed.

    Schedules the coroutine as a background task so the lifespan startup path
    is not blocked. The check is best-effort: if it fails it logs and exits
    quietly rather than crashing the server.
    """

    if not settings.scheduler_enabled:
        return

    async def _catchup() -> None:
        try:
            tz = ZoneInfo(settings.habitos_timezone)
            now = datetime.now(tz)
            scheduled_hour = settings.nightly_run_hour
            scheduled_minute = settings.nightly_run_minute

            past_scheduled_time = (now.hour, now.minute) >= (scheduled_hour, scheduled_minute)
            if not past_scheduled_time:
                return

            latest = await runs_repo.latest()
            if latest is not None:
                # Parse the date stored on the run record and compare to today.
                run_date_str = getattr(latest, "date", None) or ""
                if run_date_str == now.date().isoformat():
                    return

            log.warning(
                "Startup catch-up: no nightly run found for %s — triggering now.",
                now.date().isoformat(),
            )
            await run_job()
        except Exception:
            log.exception("Startup catch-up failed; continuing without it.")

    asyncio.ensure_future(_catchup())
