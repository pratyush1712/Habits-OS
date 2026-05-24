"""POST /habits/recompute?month=YYYY-MM."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from apps.api.deps import get_evaluation
from apps.api.routes.events import MONTH_PATTERN
from apps.api.services import HabitEvaluationService


router = APIRouter(prefix="/habits", tags=["habits"])


@router.post("/recompute")
async def recompute(
    month: str = Query(..., pattern=MONTH_PATTERN),
    service: HabitEvaluationService = Depends(get_evaluation),
) -> dict:
    return await service.recompute(month)
