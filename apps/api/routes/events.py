"""GET /events, POST /events/import-sample."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from packages.core.models import SourceEvent
from packages.core.repositories import SourceEventsRepo

from apps.api.config import load_settings
from apps.api.deps import get_events_repo, get_ingestion
from apps.api.services import EventIngestionService


MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def list_events(
    month: str | None = Query(None, pattern=MONTH_PATTERN),
    source: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    repo: SourceEventsRepo = Depends(get_events_repo),
) -> list[SourceEvent]:
    return await repo.list_events(month=month, source=source, limit=limit)


@router.post("/import-sample")
async def import_sample(
    request: Request,
    service: EventIngestionService = Depends(get_ingestion),
) -> dict:
    # Read sample path from app.state so tests can override via env easily.
    sample_path = request.app.state.sample_events_path
    if not sample_path.exists():
        raise HTTPException(404, f"sample events not found at {sample_path}")
    return await service.import_from_file(sample_path)
