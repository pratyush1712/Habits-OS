"""GET /habit-entries?month=YYYY-MM."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from packages.core.models import HabitEntry
from packages.core.repositories import HabitEntriesRepo

from apps.api.deps import get_entries_repo
from apps.api.routes.events import MONTH_PATTERN


router = APIRouter(tags=["habit-entries"])


@router.get("/habit-entries")
async def list_habit_entries(
    month: str = Query(..., pattern=MONTH_PATTERN),
    repo: HabitEntriesRepo = Depends(get_entries_repo),
) -> list[HabitEntry]:
    return await repo.list_by_month(month)
