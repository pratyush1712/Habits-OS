"""Source event inspection and sample import routes."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from packages.core.models import SourceEvent
from packages.core.repositories import SourceEventsRepo

from apps.api.deps import get_events_repo, get_ingestion
from apps.api.services import EventIngestionService


MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


class MedicationDoseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    med_key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_\-]+$")
    med_label: str = Field(min_length=1, max_length=120)
    taken_count: int = Field(ge=0, le=50)
    scheduled_count: int = Field(ge=0, le=50)
    prn: bool = False


class MedicationLogInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    doses: list[MedicationDoseInput] = Field(min_length=1, max_length=40)


class ProteinShakeLogInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    count: int = Field(default=1, ge=0, le=20)


IntakeCategory = Literal[
    "adaptogen",
    "amino_acid",
    "base",
    "cacao",
    "coffee",
    "collagen",
    "dairy",
    "drink",
    "fat",
    "fiber",
    "flavor",
    "hormone",
    "mineral",
    "mushroom",
    "nootropic",
    "probiotic",
    "stimulant",
    "substance",
    "supplement",
    "sweetener",
    "other",
]
IntakeTimeOfDay = Literal["morning", "afternoon", "evening", "night", "unknown"]


class IntakeItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_\-]+$")
    label: str = Field(min_length=1, max_length=120)
    brand_key: str = Field(default="", max_length=80, pattern=r"^$|^[a-z0-9_\-]+$")
    brand_label: str = Field(default="", max_length=120)
    product_key: str = Field(default="", max_length=80, pattern=r"^$|^[a-z0-9_\-]+$")
    product_label: str = Field(default="", max_length=120)
    ingredient_key: str = Field(default="", max_length=80, pattern=r"^$|^[a-z0-9_\-]+$")
    ingredient_label: str = Field(default="", max_length=120)
    category: IntakeCategory = "other"
    amount: float | None = Field(default=None, ge=0, le=10000)
    unit: str = Field(default="", max_length=40)
    caffeine_mg: int | None = Field(default=None, ge=0, le=2000)
    time_of_day: IntakeTimeOfDay = "unknown"
    notes: str = Field(default="", max_length=240)


class IntakeLogInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    items: list[IntakeItemInput] = Field(min_length=1, max_length=40)


def _intake_event_id(local_date: date, item: IntakeItemInput) -> str:
    return f"manual:intake-{local_date.isoformat()}-{item.key}-{item.time_of_day}"


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


@router.post("/medication")
async def log_medication_events(
    payload: MedicationLogInput,
    repo: SourceEventsRepo = Depends(get_events_repo),
) -> dict:
    try:
        tz = ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError as e:
        raise HTTPException(status_code=400, detail="unknown timezone") from e

    observed_at = datetime.combine(payload.local_date, time(hour=12), tz).astimezone(
        timezone.utc
    )
    events = [
        SourceEvent(
            id=f"manual:med-{payload.local_date.isoformat()}-{dose.med_key}",
            source="manual",
            source_event_id=f"med-{payload.local_date.isoformat()}-{dose.med_key}",
            event_type="medication",
            start_time_utc=observed_at,
            end_time_utc=None,
            local_date=payload.local_date,
            timezone=payload.timezone,
            title=dose.med_label,
            description="Manual medication/supplement dose count from the admin app.",
            metrics={
                "med_key": dose.med_key,
                "med_label": dose.med_label,
                "taken_count": dose.taken_count,
                "scheduled_count": dose.scheduled_count,
                "prn": dose.prn,
            },
        )
        for dose in payload.doses
    ]
    counts = await repo.upsert_many_counts(events)
    return {
        "month": payload.local_date.strftime("%Y-%m"),
        "local_date": payload.local_date.isoformat(),
        "events": len(events),
        "inserted": counts["inserted"],
        "updated": counts["updated"],
    }


@router.post("/protein")
@router.post("/protein-shake")
async def log_protein_shake_event(
    payload: ProteinShakeLogInput,
    repo: SourceEventsRepo = Depends(get_events_repo),
) -> dict:
    try:
        tz = ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError as e:
        raise HTTPException(status_code=400, detail="unknown timezone") from e

    observed_at = datetime.combine(payload.local_date, time(hour=12), tz).astimezone(
        timezone.utc
    )
    noun = "serving" if payload.count == 1 else "servings"
    event = SourceEvent(
        id=f"manual:protein-shake-{payload.local_date.isoformat()}",
        source="manual",
        source_event_id=f"protein-shake-{payload.local_date.isoformat()}",
        event_type="protein_shake",
        start_time_utc=observed_at,
        end_time_utc=None,
        local_date=payload.local_date,
        timezone=payload.timezone,
        title=f"{payload.count} protein {noun}",
        description="Manual protein log from the app/web app.",
        metrics={"count": payload.count},
    )
    counts = await repo.upsert_many_counts([event])
    return {
        "month": payload.local_date.strftime("%Y-%m"),
        "local_date": payload.local_date.isoformat(),
        "count": payload.count,
        "inserted": counts["inserted"],
        "updated": counts["updated"],
    }


@router.post("/intake")
async def log_intake_event(
    payload: IntakeLogInput,
    repo: SourceEventsRepo = Depends(get_events_repo),
) -> dict:
    try:
        tz = ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError as e:
        raise HTTPException(status_code=400, detail="unknown timezone") from e

    observed_at = datetime.combine(payload.local_date, time(hour=12), tz).astimezone(
        timezone.utc
    )
    events = []
    for item in payload.items:
        item_payload = item.model_dump()
        events.append(
            SourceEvent(
                id=_intake_event_id(payload.local_date, item),
                source="manual",
                source_event_id=(
                    f"intake-{payload.local_date.isoformat()}-"
                    f"{item.key}-{item.time_of_day}"
                ),
                event_type="intake",
                start_time_utc=observed_at,
                end_time_utc=None,
                local_date=payload.local_date,
                timezone=payload.timezone,
                title=item.label,
                description="Manual itemized intake log from the app/web app.",
                metrics={"count": 1, "items": [item_payload]},
            )
        )

    counts = await repo.upsert_many_counts(events)
    return {
        "month": payload.local_date.strftime("%Y-%m"),
        "local_date": payload.local_date.isoformat(),
        "items": len(events),
        "inserted": counts["inserted"],
        "updated": counts["updated"],
    }


@router.post("/import-sample")
async def import_sample(
    request: Request,
    service: EventIngestionService = Depends(get_ingestion),
) -> dict:
    sample_path = request.app.state.sample_events_path
    if not sample_path.exists():
        raise HTTPException(404, f"sample events not found at {sample_path}")
    return await service.import_from_file(sample_path)
