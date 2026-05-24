"""Source event inspection and sample import routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from packages.core.models import SourceEvent
from packages.core.repositories import SourceEventsRepo

from apps.api.deps import get_events_repo, get_ingestion
from apps.api.services import EventIngestionService


MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def list_events(
    month: str | None = Query(None, pattern=MONTH_PATTERN),
    source: str | None = Query(None),
    event_type: str | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    repo: SourceEventsRepo = Depends(get_events_repo),
) -> list[SourceEvent]:
    if month and (start or end):
        raise HTTPException(
            status_code=400,
            detail="Use either month or start/end filters, not both.",
        )
    if start and end and end < start:
        raise HTTPException(status_code=400, detail="end must be on or after start")
    return await repo.list_events(
        month=month,
        source=source,
        event_type=event_type,
        start=start,
        end=end,
        limit=limit,
    )


@router.post("/import-sample")
async def import_sample(
    request: Request,
    service: EventIngestionService = Depends(get_ingestion),
) -> dict:
    sample_path = request.app.state.sample_events_path
    if not sample_path.exists():
        raise HTTPException(404, f"sample events not found at {sample_path}")
    return await service.import_from_file(sample_path)
