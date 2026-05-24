"""GET /health — liveness + Mongo reachability."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request


router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    db = request.app.state.db
    try:
        await db.command("ping")
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "mongo": "error", "error": str(e)},
        )
    return {"status": "ok", "mongo": "connected"}
