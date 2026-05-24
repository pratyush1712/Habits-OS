"""GET /state/month?month=YYYY-MM — derived MonthHabitState."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from packages.core.models import MonthHabitState

from apps.api.deps import get_month_state
from apps.api.routes.events import MONTH_PATTERN
from apps.api.services import MonthStateService


router = APIRouter(prefix="/state", tags=["state"])


@router.get("/month")
async def month_state(
    month: str = Query(..., pattern=MONTH_PATTERN),
    service: MonthStateService = Depends(get_month_state),
) -> MonthHabitState:
    return await service.get_state(month)
