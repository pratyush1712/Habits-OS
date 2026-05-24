"""Repository for resolved habit entries (the rule engine's output)."""

from __future__ import annotations

from datetime import date
from typing import Iterable

from pymongo import ReplaceOne

from packages.core.models import Habit, HabitEntry, MonthHabitState
from packages.core.repositories.base import doc_to_model, model_to_doc, month_range


def _entry_id(d: date, habit_key: str) -> str:
    return f"{d.isoformat()}:{habit_key}"


class HabitEntriesRepo:
    COLLECTION = "habit_entries"

    def __init__(self, db) -> None:
        self.coll = db[self.COLLECTION]

    async def upsert(self, entry: HabitEntry) -> None:
        doc = model_to_doc(entry)
        doc["_id"] = _entry_id(entry.date, entry.habit_key)
        await self.coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    async def upsert_many(self, entries: Iterable[HabitEntry]) -> int:
        ops: list[ReplaceOne] = []
        for e in entries:
            doc = model_to_doc(e)
            doc["_id"] = _entry_id(e.date, e.habit_key)
            ops.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))
        if not ops:
            return 0
        result = await self.coll.bulk_write(ops, ordered=False)
        return result.upserted_count + result.modified_count

    async def get(self, day: date, habit_key: str) -> HabitEntry | None:
        doc = await self.coll.find_one({"_id": _entry_id(day, habit_key)})
        return doc_to_model(doc, HabitEntry) if doc else None

    async def list_by_month(self, month: str) -> list[HabitEntry]:
        start, end = month_range(month)
        cursor = self.coll.find({"date": {"$gte": start, "$lt": end}}).sort(
            [("date", 1), ("habit_key", 1)]
        )
        return [doc_to_model(d, HabitEntry) async for d in cursor]

    async def get_state(self, month: str, habits: Iterable[Habit]) -> MonthHabitState:
        """Assemble a MonthHabitState — the renderer-shaped view of a month."""
        entries = await self.list_by_month(month)
        return MonthHabitState(month=month, habits=list(habits), entries=entries)

    async def delete_month(self, month: str) -> int:
        """Wipe a month — used before re-evaluating with a changed ruleset."""
        start, end = month_range(month)
        result = await self.coll.delete_many({"date": {"$gte": start, "$lt": end}})
        return result.deleted_count
