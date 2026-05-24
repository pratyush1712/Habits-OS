"""Repository for the habit catalog."""

from __future__ import annotations

from typing import Iterable

from pymongo import ReplaceOne

from packages.core.models import Habit
from packages.core.repositories.base import doc_to_model, model_to_doc, now_utc


def _to_habit(doc: dict) -> Habit:
    """Strip storage-only fields (archived_at) before validating into Habit."""
    raw = dict(doc)
    raw.pop("_id", None)
    raw.pop("archived_at", None)
    return Habit.model_validate(raw)


class HabitsRepo:
    COLLECTION = "habits"

    def __init__(self, db) -> None:
        self.coll = db[self.COLLECTION]

    async def upsert(self, habit: Habit) -> None:
        doc = model_to_doc(habit)
        # $setOnInsert preserves an existing archived_at across upserts.
        await self.coll.update_one(
            {"_id": habit.key},
            {"$set": doc, "$setOnInsert": {"archived_at": None}},
            upsert=True,
        )

    async def upsert_many(self, habits: Iterable[Habit]) -> int:
        ops: list[ReplaceOne] = []
        for h in habits:
            ops.append(
                ReplaceOne(
                    {"_id": h.key},
                    {**model_to_doc(h), "archived_at": None},
                    upsert=True,
                )
            )
        if not ops:
            return 0
        result = await self.coll.bulk_write(ops, ordered=False)
        return result.upserted_count + result.modified_count

    async def get(self, key: str) -> Habit | None:
        doc = await self.coll.find_one({"_id": key})
        return _to_habit(doc) if doc else None

    async def list_active(self) -> list[Habit]:
        cursor = self.coll.find({"archived_at": None, "enabled": True}).sort(
            [("sort_order", 1), ("_id", 1)]
        )
        return [_to_habit(d) async for d in cursor]

    async def list_all(self) -> list[Habit]:
        cursor = self.coll.find().sort("_id", 1)
        return [_to_habit(d) async for d in cursor]

    async def archive(self, key: str) -> bool:
        result = await self.coll.update_one(
            {"_id": key}, {"$set": {"archived_at": now_utc()}}
        )
        return result.modified_count > 0

    async def count_all(self) -> int:
        return await self.coll.count_documents({})
