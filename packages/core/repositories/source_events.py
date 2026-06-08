"""Repository for normalized source events."""

from __future__ import annotations

from datetime import date
from typing import Iterable

from pymongo import ReplaceOne
from pymongo.results import BulkWriteResult

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
        result = await self.upsert_many_counts(events)
        return result["inserted"] + result["updated"]

    async def upsert_many_counts(self, events: Iterable[SourceEvent]) -> dict[str, int]:
        ops: list[ReplaceOne] = []
        for e in events:
            doc = model_to_doc(e)
            doc["_id"] = e.id
            ops.append(ReplaceOne({"_id": e.id}, doc, upsert=True))
        if not ops:
            return {"inserted": 0, "updated": 0, "total": 0}
        result: BulkWriteResult = await self.coll.bulk_write(ops, ordered=False)
        inserted = result.upserted_count
        updated = result.modified_count
        return {"inserted": inserted, "updated": updated, "total": inserted + updated}

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

    async def delete_by_source_date_range_except(
        self,
        *,
        source: str,
        start: date,
        end: date,
        keep_ids: set[str],
        event_type: str | None = None,
    ) -> int:
        query: dict = {
            "source": source,
            "local_date": {"$gte": start.isoformat(), "$lte": end.isoformat()},
        }
        if event_type is not None:
            query["event_type"] = event_type
        if keep_ids:
            query["_id"] = {"$nin": sorted(keep_ids)}
        result = await self.coll.delete_many(query)
        return result.deleted_count

    async def list_events(
        self,
        *,
        month: str | None = None,
        source: str | None = None,
        event_type: str | None = None,
        start: date | None = None,
        end: date | None = None,
        limit: int = 100,
    ) -> list[SourceEvent]:
        """Flexible query for the debugging GET /events route."""
        query: dict = {}
        if month:
            range_start, range_end = month_range(month)
            query["local_date"] = {"$gte": range_start, "$lt": range_end}
        elif start or end:
            local_date_filter: dict[str, str] = {}
            if start:
                local_date_filter["$gte"] = start.isoformat()
            if end:
                local_date_filter["$lte"] = end.isoformat()
            query["local_date"] = local_date_filter
        if source:
            query["source"] = source
        if event_type:
            query["event_type"] = event_type
        cursor = (
            self.coll.find(query)
            .sort([("local_date", -1), ("start_time_utc", -1)])
            .limit(limit)
        )
        return [doc_to_model(d, SourceEvent, id_field="id") async for d in cursor]

    async def delete(self, event_id: str) -> bool:
        result = await self.coll.delete_one({"_id": event_id})
        return result.deleted_count > 0
