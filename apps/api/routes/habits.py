"""Habit catalog + recompute routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from apps.api.deps import get_evaluation, get_habit_catalog
from apps.api.routes.events import MONTH_PATTERN
from apps.api.services import HabitCatalogService, HabitEvaluationService
from packages.core.models import Habit


router = APIRouter(prefix="/habits", tags=["habits"])


class SeedDefaultsResponse(BaseModel):
    seeded: int
    total_active: int
    retired: list[str] = []
    message: str


@router.get("")
async def list_habits(
    service: HabitCatalogService = Depends(get_habit_catalog),
) -> list[Habit]:
    return await service.list_active()


@router.post("/seed-defaults")
async def seed_defaults(
    service: HabitCatalogService = Depends(get_habit_catalog),
) -> SeedDefaultsResponse:
    result = await service.seed_default_habits()
    return SeedDefaultsResponse.model_validate(result)


@router.post("/recompute")
async def recompute(
    month: str = Query(..., pattern=MONTH_PATTERN),
    service: HabitEvaluationService = Depends(get_evaluation),
) -> dict:
    return await service.recompute(month)
