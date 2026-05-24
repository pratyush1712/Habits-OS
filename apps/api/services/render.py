"""Orchestrate a PDF render and record an audit-trail RenderJob."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from packages.core.models import RenderJob, RenderTrigger
from packages.core.repositories import RenderJobsRepo
from packages.renderer.render_month import render as render_pdf

from apps.api.services.month_state import MonthStateService


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RenderService:
    def __init__(
        self,
        jobs_repo: RenderJobsRepo,
        month_state: MonthStateService,
        output_dir: Path,
    ) -> None:
        self.jobs_repo = jobs_repo
        self.month_state = month_state
        self.output_dir = output_dir

    async def render(self, month: str, *, triggered_by: RenderTrigger = "manual") -> RenderJob:
        job = RenderJob(month=month, triggered_by=triggered_by)
        job_id = await self.jobs_repo.create(job)
        await self.jobs_repo.update_status(job_id, status="running", started_at=_now())

        try:
            state = await self.month_state.get_state(month)
            # Playwright's sync API refuses to run inside an asyncio loop, so
            # offload to a worker thread (which has no loop of its own).
            pdf_path = await asyncio.to_thread(render_pdf, state, self.output_dir)
            await self.jobs_repo.update_status(
                job_id,
                status="completed",
                finished_at=_now(),
                output_path=str(pdf_path),
            )
        except Exception as e:
            await self.jobs_repo.update_status(
                job_id,
                status="failed",
                finished_at=_now(),
                error=f"{type(e).__name__}: {e}",
            )
            raise

        result = await self.jobs_repo.get(job_id)
        assert result is not None
        return result
