"""Day One status and manual sync routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.deps import get_dayone_sync_service
from apps.api.services.dayone_sync import DayOneSyncService, summary_to_status_dict


router = APIRouter(prefix="/dayone", tags=["dayone"])


@router.get("/status")
async def dayone_status(service: DayOneSyncService = Depends(get_dayone_sync_service)) -> dict:
    return await service.status()


@router.post("/sync")
async def sync_dayone(
    start: date = Query(...),
    end: date = Query(...),
    recompute: bool = Query(True),
    service: DayOneSyncService = Depends(get_dayone_sync_service),
) -> dict:
    if end < start:
        raise HTTPException(status_code=400, detail="end must be on or after start")
    summary = await service.sync_range(start=start, end=end, recompute=recompute)
    return summary_to_status_dict(summary)
