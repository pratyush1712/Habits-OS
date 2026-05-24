"""WHOOP OAuth/status/manual sync routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from apps.api.deps import get_whoop_sync_service
from apps.api.services.whoop_sync import WhoopSyncService
from packages.connectors.whoop.auth import WhoopOAuthError
from packages.connectors.whoop.client import WhoopApiError
from packages.core.models import SourceAccount


router = APIRouter(prefix="/whoop", tags=["whoop"])


@router.get("/oauth/start")
def start_oauth(
    request: Request,
    service: WhoopSyncService = Depends(get_whoop_sync_service),
) -> dict:
    try:
        auth = service.authorization()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _oauth_state_store(request).add(auth.state)
    return {
        "authorization_url": auth.authorization_url,
        "state": auth.state,
        "scopes": auth.scopes,
    }


@router.get("/oauth/callback")
async def complete_oauth(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    service: WhoopSyncService = Depends(get_whoop_sync_service),
) -> SourceAccount:
    state_store = _oauth_state_store(request)
    if state not in state_store:
        raise HTTPException(status_code=400, detail="invalid oauth state")
    state_store.remove(state)
    try:
        return await service.complete_oauth(code)
    except WhoopApiError as e:
        raise HTTPException(status_code=_whoop_status_code(e), detail=str(e)) from e
    except WhoopOAuthError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/status")
async def whoop_status(service: WhoopSyncService = Depends(get_whoop_sync_service)) -> dict:
    return await service.status()


@router.post("/sync")
async def sync_whoop(
    external_user_id: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    recompute: bool = Query(True),
    service: WhoopSyncService = Depends(get_whoop_sync_service),
) -> dict:
    if end < start:
        raise HTTPException(status_code=400, detail="end must be on or after start")
    try:
        return await service.sync_range(
            external_user_id=external_user_id,
            start=start,
            end=end,
            recompute=recompute,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except WhoopOAuthError as e:
        detail = {
            "integration": "whoop",
            "error": str(e),
            "diagnostic": "WHOOP token is missing or cannot be refreshed; re-authorize.",
        }
        raise HTTPException(status_code=401, detail=detail) from e
    except WhoopApiError as e:
        detail = {"integration": "whoop", "error": str(e), "status_code": e.status_code}
        if e.status_code == 401:
            detail["diagnostic"] = "WHOOP token unauthorized; re-run OAuth authorization."
        raise HTTPException(status_code=_whoop_status_code(e), detail=detail) from e


def _whoop_status_code(error: WhoopApiError) -> int:
    if error.status_code == 401:
        return 401
    if error.status_code == 429:
        return 429
    return 502


def _oauth_state_store(request: Request) -> set[str]:
    store = getattr(request.app.state, "whoop_oauth_states", None)
    if store is None:
        store = set()
        request.app.state.whoop_oauth_states = store
    return store
