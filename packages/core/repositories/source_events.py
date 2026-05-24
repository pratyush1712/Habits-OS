"""Repository for normalized source events."""

from __future__ import annotations

from datetime import date
from typing import Iterable

from pymongo import ReplaceOne

from packages.core.models import SourceEvent
from packages.core.repositories.base import doc_to_model, model_to_doc, month_range


class SourceEventsRepo:
    COLLECTION = "source_events"

    def __init__(self, db) -> None:
        self.coll = db[self.COLLECTION]

    async def upsert(self, event: SourceEvent) -> None:
        doc = model_to_doc(event)
        doc["_id"] = event.id
        await self.coll.replace_one({"_id": event.id}, doc, upsert=True)

    async def upsert_many(self, events: Iterable[SourceEvent]) -> int:
        ops: list[ReplaceOne] = []
        for e in events:
            doc = model_to_doc(e)
            doc["_id"] = e.id
            ops.append(ReplaceOne({"_id": e.id}, doc, upsert=True))
        if not ops:
            return 0
        result = await self.coll.bulk_write(ops, ordered=False)
        return result.upserted_count + result.modified_count

    async def get(self, event_id: str) -> SourceEvent | None:
        doc = await self.coll.find_one({"_id": event_id})
        return doc_to_model(doc, SourceEvent, id_field="id") if doc else None

    async def list_by_local_date(self, day: date) -> list[SourceEvent]:
        cursor = self.coll.find({"local_date": day.isoformat()}).sort("start_time_utc", 1)
        return [doc_to_model(d, SourceEvent, id_field="id") async for d in cursor]

    async def list_by_month(self, month: str) -> list[SourceEvent]:
        start, end = month_range(month)
        cursor = self.coll.find({"local_date": {"$gte": start, "$lt": end}}).sort(
            [("local_date", 1), ("start_time_utc", 1)]
        )
        return [doc_to_model(d, SourceEvent, id_field="id") async for d in cursor]

    async def list_events(
        self,
        *,
        month: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[SourceEvent]:
        """Flexible query for the debugging GET /events route."""
        query: dict = {}
        if month:
            start, end = month_range(month)
            query["local_date"] = {"$gte": start, "$lt": end}
        if source:
            query["source"] = source
        cursor = (
            self.coll.find(query)
            .sort([("local_date", -1), ("start_time_utc", -1)])
            .limit(limit)
        )
        return [doc_to_model(d, SourceEvent, id_field="id") async for d in cursor]

    async def delete(self, event_id: str) -> bool:
        result = await self.coll.delete_one({"_id": event_id})
        return result.deleted_count > 0
