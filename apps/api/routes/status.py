"""GET /status — local control-surface summary."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from apps.api.deps import get_status_service
from apps.api.services.status import StatusService


router = APIRouter(tags=["status"])


@router.get("/status")
async def status(service: StatusService = Depends(get_status_service)) -> dict:
    summary = await service.status()
    if not summary["mongo"]["connected"]:
        raise HTTPException(status_code=503, detail=summary)
    return summary
