"""Automation status and manual trigger routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from apps.api.deps import get_automation_service
from apps.api.routes.events import MONTH_PATTERN
from apps.api.services.automation import AutomationService


router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/status")
async def automation_status(
    request: Request,
    service: AutomationService = Depends(get_automation_service),
) -> dict:
    return await service.status(getattr(request.app.state, "scheduler", None))


@router.post("/nightly-run")
async def nightly_run(
    dry_run: bool = Query(True),
    service: AutomationService = Depends(get_automation_service),
) -> dict:
    try:
        return await service.run_nightly_pipeline(dry_run=dry_run, triggered_by="manual")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/month-rollover")
async def month_rollover(
    from_month: str = Query(..., pattern=MONTH_PATTERN),
    to_month: str = Query(..., pattern=MONTH_PATTERN),
    dry_run: bool = Query(True),
    service: AutomationService = Depends(get_automation_service),
) -> dict:
    try:
        return await service.run_month_rollover(from_month, to_month, dry_run=dry_run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
