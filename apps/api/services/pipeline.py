"""Manual month pipeline orchestration for the local API."""

from __future__ import annotations

from datetime import date

from apps.api.errors import ExternalServiceError, InvalidOperationError
from apps.api.services.habit_evaluation import HabitEvaluationService
from apps.api.services.render import RenderService
from apps.api.services.remarkable_sync import RemarkableSyncService
from apps.api.services.whoop_sync import WhoopSyncService
from packages.connectors.whoop.client import WhoopApiError


class PipelineRenderError(ExternalServiceError):
    def __init__(self, detail: dict) -> None:
        super().__init__("render failed")
        self.detail = detail


class PipelineService:
    def __init__(
        self,
        whoop: WhoopSyncService,
        habits: HabitEvaluationService,
        render: RenderService,
        remarkable: RemarkableSyncService,
    ) -> None:
        self.whoop = whoop
        self.habits = habits
        self.render = render
        self.remarkable = remarkable

    async def run_month(
        self,
        *,
        external_user_id: str,
        start: date,
        end: date,
        month: str,
        upload: bool = False,
        dry_run: bool = True,
    ) -> dict:
        if end < start:
            raise InvalidOperationError("end must be on or after start")

        summary: dict = {
            "range": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "month": month,
            },
            "whoop": None,
            "habits": None,
            "render": None,
            "remarkable": {"attempted": False, "status": "skipped"},
        }

        whoop_result = await self.whoop.sync_range(
            external_user_id=external_user_id,
            start=start,
            end=end,
            recompute=False,
        )
        summary["whoop"] = _pipeline_whoop_summary(whoop_result)

        habit_result = await self.habits.recompute(month)
        summary["habits"] = {
            "recomputed": habit_result["entries_written"],
            "month": month,
            "entries_deleted": habit_result["entries_deleted"],
            "events": habit_result["events"],
            "overrides": habit_result["overrides"],
        }

        try:
            render_job = await self.render.render(month, triggered_by="manual")
        except Exception as e:
            summary["render"] = {
                "status": "failed",
                "error": f"{type(e).__name__}: {e}",
            }
            summary["remarkable"] = {
                "attempted": False,
                "status": "skipped",
                "reason": "render_failed",
            }
            raise PipelineRenderError(summary) from e

        summary["render"] = {
            "status": render_job.status,
            "job_id": render_job.id,
            "pdf_path": render_job.output_path,
        }

        if upload:
            try:
                sync_result = await self.remarkable.sync_latest_month(
                    month,
                    dry_run=dry_run,
                    update=False,
                )
                summary["remarkable"] = {
                    "attempted": True,
                    "status": sync_result.status,
                    "dry_run": sync_result.dry_run,
                    "device_mutated": sync_result.device_mutated,
                    "target_path": sync_result.target_path,
                    "message": sync_result.message,
                    "instructions": sync_result.instructions,
                }
            except Exception as e:
                summary["remarkable"] = {
                    "attempted": True,
                    "status": "failed",
                    "error": f"{type(e).__name__}: {e}",
                    "pdf_preserved": render_job.output_path,
                }
        return summary


def _pipeline_whoop_summary(result: dict) -> dict:
    written = result.get("written")
    if isinstance(written, dict):
        return {
            "workouts": written.get("workouts", {"inserted": 0, "updated": result["workouts"]}),
            "sleeps": written.get("sleeps", {"inserted": 0, "updated": result["sleeps"]}),
            "recoveries": written.get(
                "recoveries", {"inserted": 0, "updated": result["recoveries"]}
            ),
            "events_written": result["events_written"],
        }
    return {
        "workouts": {"inserted": 0, "updated": result["workouts"]},
        "sleeps": {"inserted": 0, "updated": result["sleeps"]},
        "recoveries": {"inserted": 0, "updated": result["recoveries"]},
        "events_written": result["events_written"],
    }


def whoop_http_status(error: WhoopApiError) -> int:
    if error.status_code == 401:
        return 401
    if error.status_code == 429:
        return 429
    return 502
