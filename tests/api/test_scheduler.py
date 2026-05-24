from __future__ import annotations

from dataclasses import dataclass

from apps.api.scheduler import build_scheduler


@dataclass(frozen=True)
class _Settings:
    scheduler_enabled: bool
    nightly_run_hour: int = 3
    nightly_run_minute: int = 0
    habitos_timezone: str = "America/New_York"


class _Scheduler:
    def __init__(self, *, timezone: str) -> None:
        self.timezone = timezone
        self.jobs: list[dict] = []
        self.started = False

    def add_job(self, func, trigger, *, id: str, replace_existing: bool) -> None:
        self.jobs.append(
            {
                "func": func,
                "trigger": trigger,
                "id": id,
                "replace_existing": replace_existing,
            }
        )

    def start(self) -> None:
        self.started = True


def test_build_scheduler_returns_none_when_disabled():
    scheduler = build_scheduler(
        settings=_Settings(scheduler_enabled=False),
        run_job=lambda: None,
        scheduler_factory=_Scheduler,
    )

    assert scheduler is None


def test_build_scheduler_registers_nightly_job_when_enabled():
    scheduler = build_scheduler(
        settings=_Settings(scheduler_enabled=True, nightly_run_hour=4, nightly_run_minute=30),
        run_job=lambda: None,
        scheduler_factory=_Scheduler,
    )

    assert scheduler is not None
    assert scheduler.started is True
    assert scheduler.timezone == "America/New_York"
    assert scheduler.jobs[0]["id"] == "habitos-nightly"
    assert scheduler.jobs[0]["replace_existing"] is True
