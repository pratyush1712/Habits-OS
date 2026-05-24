"""POST /render/month, GET /render/jobs, GET /render/latest."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.core.models import RenderJob
from packages.core.repositories import RenderJobsRepo

from apps.api.deps import get_jobs_repo, get_render_service
from apps.api.routes.events import MONTH_PATTERN
from apps.api.services import RenderService


router = APIRouter(prefix="/render", tags=["render"])


@router.post("/month")
async def render_month(
    month: str = Query(..., pattern=MONTH_PATTERN),
    service: RenderService = Depends(get_render_service),
) -> RenderJob:
    try:
        return await service.render(month)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "failed", "error": f"{type(e).__name__}: {e}"},
        ) from e


@router.get("/jobs")
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    repo: RenderJobsRepo = Depends(get_jobs_repo),
) -> list[RenderJob]:
    return await repo.list_recent(limit)


@router.get("/latest")
async def latest(
    month: str | None = Query(None, pattern=MONTH_PATTERN),
    repo: RenderJobsRepo = Depends(get_jobs_repo),
) -> RenderJob:
    job = await repo.latest_for_month(month) if month else await repo.latest()
    if job is None:
        raise HTTPException(404, "no renders yet")
    return job
