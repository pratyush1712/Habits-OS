"""Repository for user-asserted habit overrides."""

from __future__ import annotations

from datetime import date

from packages.core.models import HabitOverride
from packages.core.repositories.base import doc_to_model, model_to_doc, month_range


def _override_id(d: date, habit_key: str) -> str:
    return f"{d.isoformat()}:{habit_key}"


class ManualOverridesRepo:
    COLLECTION = "manual_overrides"

    def __init__(self, db) -> None:
        self.coll = db[self.COLLECTION]

    async def upsert(self, override: HabitOverride) -> None:
        doc = model_to_doc(override)
        doc["_id"] = _override_id(override.date, override.habit_key)
        await self.coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    async def get(self, day: date, habit_key: str) -> HabitOverride | None:
        doc = await self.coll.find_one({"_id": _override_id(day, habit_key)})
        return doc_to_model(doc, HabitOverride) if doc else None

    async def list_by_month(self, month: str) -> list[HabitOverride]:
        start, end = month_range(month)
        cursor = self.coll.find({"date": {"$gte": start, "$lt": end}}).sort(
            [("date", 1), ("habit_key", 1)]
        )
        return [doc_to_model(d, HabitOverride) async for d in cursor]

    async def delete(self, day: date, habit_key: str) -> bool:
        result = await self.coll.delete_one({"_id": _override_id(day, habit_key)})
        return result.deleted_count > 0
