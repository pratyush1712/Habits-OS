"""Repository for the PDF render audit trail.

Unlike the other collections, render_jobs uses ObjectId for `_id` because
there is no natural key: many renders of the same month over time are valid.
ObjectId never leaks past this module — the model exposes `id: str`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from packages.core.models import RenderJob, RenderJobStatus
from packages.core.repositories.base import doc_to_model, model_to_doc


class RenderJobsRepo:
    COLLECTION = "render_jobs"

    def __init__(self, db) -> None:
        self.coll = db[self.COLLECTION]

    async def create(self, job: RenderJob) -> str:
        doc = model_to_doc(job)
        result = await self.coll.insert_one(doc)
        return str(result.inserted_id)

    async def get(self, job_id: str) -> RenderJob | None:
        doc = await self.coll.find_one({"_id": ObjectId(job_id)})
        return doc_to_model(doc, RenderJob, id_field="id") if doc else None

    async def update_status(
        self,
        job_id: str,
        *,
        status: RenderJobStatus,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        output_path: str | None = None,
        error: str | None = None,
    ) -> bool:
        update: dict[str, Any] = {"status": status}
        if started_at is not None:
            update["started_at"] = started_at
        if finished_at is not None:
            update["finished_at"] = finished_at
        if output_path is not None:
            update["output_path"] = output_path
        if error is not None:
            update["error"] = error
        result = await self.coll.update_one({"_id": ObjectId(job_id)}, {"$set": update})
        return result.modified_count > 0

    async def latest_for_month(self, month: str) -> RenderJob | None:
        doc = await self.coll.find_one({"month": month}, sort=[("requested_at", -1)])
        return doc_to_model(doc, RenderJob, id_field="id") if doc else None

    async def list_by_status(self, status: RenderJobStatus, limit: int = 50) -> list[RenderJob]:
        cursor = self.coll.find({"status": status}).sort("requested_at", -1).limit(limit)
        return [doc_to_model(d, RenderJob, id_field="id") async for d in cursor]

    async def list_recent(self, limit: int = 50) -> list[RenderJob]:
        cursor = self.coll.find().sort("requested_at", -1).limit(limit)
        return [doc_to_model(d, RenderJob, id_field="id") async for d in cursor]

    async def latest(self) -> RenderJob | None:
        doc = await self.coll.find_one({}, sort=[("requested_at", -1)])
        return doc_to_model(doc, RenderJob, id_field="id") if doc else None
