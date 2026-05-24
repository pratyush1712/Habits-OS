"""Nightly automation orchestration for HabitOS."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from packages.core.models import AutomationRun, RenderJob
from packages.core.repositories import AutomationRunsRepo
from packages.remarkable_sync import SyncResult

from apps.api.services.habit_evaluation import HabitEvaluationService
from apps.api.services.remarkable_lifecycle import RemarkableLifecycleService
from apps.api.services.render import RenderService
from apps.api.services.whoop_sync import WhoopSyncService


class AutomationService:
    """Run the nightly WHOOP → recompute → render → reMarkable flow."""

    def __init__(
        self,
        *,
        settings,
        whoop: WhoopSyncService,
        habits: HabitEvaluationService,
        render: RenderService,
        lifecycle: RemarkableLifecycleService,
        runs_repo: AutomationRunsRepo,
    ) -> None:
        self.settings = settings
        self.whoop = whoop
        self.habits = habits
        self.render = render
        self.lifecycle = lifecycle
        self.runs_repo = runs_repo

    async def status(self, scheduler=None) -> dict:
        latest = await self.runs_repo.latest()
        next_run_time = getattr(scheduler, "get_job", lambda *_args, **_kwargs: None)(
            "habitos-nightly"
        )
        next_run_at = None
        if next_run_time is not None and getattr(next_run_time, "next_run_time", None) is not None:
            next_run_at = next_run_time.next_run_time.isoformat()
        return {
            "scheduler": {
                "enabled": self.settings.scheduler_enabled,
                "running": scheduler is not None,
                "next_run_at": next_run_at,
            },
            "timezone": self.settings.habitos_timezone,
            "reconcile_days": self.settings.reconcile_days,
            "default_whoop_external_user_id_configured": bool(
                self.settings.default_whoop_external_user_id
            ),
            "auto_upload_remarkable": self.settings.auto_upload_remarkable,
            "remarkable_dry_run": self.settings.remarkable_dry_run,
            "latest_run": latest.model_dump(mode="json") if latest is not None else None,
        }

    async def run_nightly_pipeline(
        self,
        today: date | None = None,
        dry_run: bool | None = None,
        triggered_by: str = "manual",
    ) -> dict:
        resolved_today = today or self._local_today()
        effective_dry_run = self.settings.remarkable_dry_run if dry_run is None else dry_run
        current_month = _month_from_date(resolved_today)
        previous_month = _previous_month(current_month) if resolved_today.day == 1 else None
        start = resolved_today - timedelta(days=self.settings.reconcile_days)
        end = resolved_today
        affected_months = _affected_months(start, end)
        summary = {
            "date": resolved_today.isoformat(),
            "timezone": self.settings.habitos_timezone,
            "dry_run": effective_dry_run,
            "window": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "reconcile_days": self.settings.reconcile_days,
            },
            "months": {
                "current": current_month,
                "previous": previous_month,
                "affected": affected_months,
            },
            "rollover": {"detected": previous_month is not None},
            "whoop": {},
            "habits": [],
            "render": {},
            "remarkable": {},
        }
        run_id = await self.runs_repo.create(
            AutomationRun(
                run_type="nightly" if triggered_by == "nightly" else "manual",
                status="running",
                dry_run=effective_dry_run,
                timezone=self.settings.habitos_timezone,
                date=resolved_today.isoformat(),
                window=summary["window"],
                months=summary["months"],
            )
        )

        try:
            external_user_id = self.settings.default_whoop_external_user_id
            if not external_user_id:
                raise ValueError(
                    "HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID is required for nightly automation"
                )

            summary["whoop"] = await self.whoop.sync_range(
                external_user_id=external_user_id,
                start=start,
                end=end,
                recompute=False,
            )
            summary["habits"] = [
                await self.habits.recompute(month) for month in affected_months
            ]

            current_job = await self.render.render(current_month, triggered_by="schedule")
            summary["render"]["current"] = _render_job_summary(current_job)

            if previous_month is not None:
                previous_job = await self.render.render(previous_month, triggered_by="schedule")
                summary["render"]["previous"] = _render_job_summary(previous_job)
                summary["remarkable"]["archive"] = _sync_result_summary(
                    await self.lifecycle.prepare_archive_previous_month(
                        previous_month,
                        dry_run=effective_dry_run,
                    )
                )

            if self.settings.auto_upload_remarkable:
                current_pdf_path = Path(current_job.output_path or "")
                summary["remarkable"]["current"] = _sync_result_summary(
                    await self.lifecycle.prepare_current_month_upload(
                        current_month,
                        current_pdf_path,
                        dry_run=effective_dry_run,
                    )
                )
            else:
                summary["remarkable"]["current"] = {
                    "attempted": False,
                    "status": "skipped",
                }

            await self.runs_repo.complete(
                run_id,
                finished_at=_now_utc(),
                whoop_summary=summary["whoop"],
                habit_recompute_summary=summary["habits"],
                render_summary=summary["render"],
                remarkable_summary=summary["remarkable"],
            )
            summary["run_id"] = run_id
            summary["run_type"] = "nightly" if triggered_by == "nightly" else "manual"
            return summary
        except Exception as exc:
            summary["error"] = f"{type(exc).__name__}: {exc}"
            await self.runs_repo.fail(
                run_id,
                finished_at=_now_utc(),
                error=summary["error"],
                whoop_summary=summary["whoop"],
                habit_recompute_summary=summary["habits"],
                render_summary=summary["render"],
                remarkable_summary=summary["remarkable"],
            )
            raise

    async def run_month_rollover(
        self,
        from_month: str,
        to_month: str,
        *,
        dry_run: bool,
    ) -> dict:
        if _next_month(from_month) != to_month:
            raise ValueError("to_month must be the month immediately after from_month")

        summary = {
            "from_month": from_month,
            "to_month": to_month,
            "dry_run": dry_run,
            "render": {},
            "remarkable": {},
        }
        run_id = await self.runs_repo.create(
            AutomationRun(
                run_type="rollover",
                status="running",
                dry_run=dry_run,
                timezone=self.settings.habitos_timezone,
                date=self._local_today().isoformat(),
                window={
                    "start": self._local_today().isoformat(),
                    "end": self._local_today().isoformat(),
                    "reconcile_days": self.settings.reconcile_days,
                },
                months={
                    "current": to_month,
                    "previous": from_month,
                    "affected": [from_month, to_month],
                },
            )
        )

        try:
            previous_job = await self.render.render(from_month, triggered_by="schedule")
            current_job = await self.render.render(to_month, triggered_by="schedule")
            summary["render"]["previous"] = _render_job_summary(previous_job)
            summary["render"]["current"] = _render_job_summary(current_job)
            summary["remarkable"]["archive"] = _sync_result_summary(
                await self.lifecycle.prepare_archive_previous_month(from_month, dry_run=dry_run)
            )
            if self.settings.auto_upload_remarkable:
                summary["remarkable"]["current"] = _sync_result_summary(
                    await self.lifecycle.prepare_current_month_upload(
                        to_month,
                        Path(current_job.output_path or ""),
                        dry_run=dry_run,
                    )
                )
            else:
                summary["remarkable"]["current"] = {
                    "attempted": False,
                    "status": "skipped",
                }
            await self.runs_repo.complete(
                run_id,
                finished_at=_now_utc(),
                whoop_summary={},
                habit_recompute_summary=[],
                render_summary=summary["render"],
                remarkable_summary=summary["remarkable"],
            )
            summary["run_id"] = run_id
            return summary
        except Exception as exc:
            await self.runs_repo.fail(
                run_id,
                finished_at=_now_utc(),
                error=f"{type(exc).__name__}: {exc}",
                render_summary=summary["render"],
                remarkable_summary=summary["remarkable"],
            )
            raise

    def _local_today(self) -> date:
        return datetime.now(ZoneInfo(self.settings.habitos_timezone)).date()


def _now_utc() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


def _month_from_date(value: date) -> str:
    return value.strftime("%Y-%m")


def _previous_month(month: str) -> str:
    year, month_num = _parse_month(month)
    if month_num == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month_num - 1:02d}"


def _next_month(month: str) -> str:
    year, month_num = _parse_month(month)
    if month_num == 12:
        return f"{year + 1:04d}-01"
    return f"{year:04d}-{month_num + 1:02d}"


def _affected_months(start: date, end: date) -> list[str]:
    months: list[str] = []
    cursor = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while cursor <= end_month:
        months.append(cursor.strftime("%Y-%m"))
        cursor = date(*_next_month_parts(cursor.year, cursor.month), 1)
    return months


def _next_month_parts(year: int, month_num: int) -> tuple[int, int]:
    if month_num == 12:
        return year + 1, 1
    return year, month_num + 1


def _parse_month(month: str) -> tuple[int, int]:
    year_s, month_s = month.split("-")
    return int(year_s), int(month_s)


def _render_job_summary(job: RenderJob) -> dict:
    return {
        "job_id": job.id,
        "month": job.month,
        "status": job.status,
        "pdf_path": job.output_path,
    }


def _sync_result_summary(result: SyncResult) -> dict:
    return {
        "attempted": True,
        "adapter": result.adapter,
        "action": result.action,
        "dry_run": result.dry_run,
        "status": result.status,
        "target_path": result.target_path,
        "message": result.message,
        "device_mutated": result.device_mutated,
        "instructions": result.instructions,
        "local_pdf_path": str(result.local_pdf_path) if result.local_pdf_path else None,
    }
