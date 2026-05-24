from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.deps import get_whoop_sync_service
from apps.api.services.whoop_sync import WhoopSyncService
from packages.core.models import SourceAccount


router = APIRouter(prefix="/whoop", tags=["whoop"])


@router.get("/oauth/start")
def start_oauth(service: WhoopSyncService = Depends(get_whoop_sync_service)) -> dict:
    try:
        auth = service.authorization()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "authorization_url": auth.authorization_url,
        "state": auth.state,
        "scopes": auth.scopes,
    }


@router.post("/oauth/callback")
async def complete_oauth(
    code: str = Query(...),
    service: WhoopSyncService = Depends(get_whoop_sync_service),
) -> SourceAccount:
    try:
        return await service.complete_oauth(code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/sync")
async def sync_whoop(
    external_user_id: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    recompute: bool = Query(True),
    service: WhoopSyncService = Depends(get_whoop_sync_service),
) -> dict:
    if end <= start:
        raise HTTPException(status_code=400, detail="end must be after start")
    try:
        return await service.sync_range(
            external_user_id=external_user_id,
            start=start,
            end=end,
            recompute=recompute,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
