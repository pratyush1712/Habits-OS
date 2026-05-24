"""reMarkable manual sync/upload routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.deps import get_remarkable_sync_service
from apps.api.routes.events import MONTH_PATTERN
from apps.api.services.remarkable_sync import RemarkableSyncService
from packages.remarkable_sync import SyncResult


router = APIRouter(prefix="/remarkable", tags=["remarkable"])


@router.get("/status")
async def remarkable_status(
    service: RemarkableSyncService = Depends(get_remarkable_sync_service),
) -> dict:
    return await service.status()


@router.post("/upload")
async def upload_month(
    month: str = Query(..., pattern=MONTH_PATTERN),
    dry_run: bool = Query(True),
    update: bool = Query(False),
    service: RemarkableSyncService = Depends(get_remarkable_sync_service),
) -> SyncResult:
    try:
        return await service.sync_latest_month(month, dry_run=dry_run, update=update)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/sync")
async def sync_month(
    month: str = Query(..., pattern=MONTH_PATTERN),
    dry_run: bool = Query(True),
    update: bool = Query(False),
    service: RemarkableSyncService = Depends(get_remarkable_sync_service),
) -> SyncResult:
    return await upload_month(month=month, dry_run=dry_run, update=update, service=service)


@router.get("/instructions")
async def sync_instructions(
    month: str = Query(..., pattern=MONTH_PATTERN),
    service: RemarkableSyncService = Depends(get_remarkable_sync_service),
) -> SyncResult:
    try:
        return await service.sync_latest_month(month, dry_run=True, update=False)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
