"""Repository for append-only automation run audit records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId

from packages.core.models import AutomationRun
from packages.core.repositories.base import doc_to_model, model_to_doc


class AutomationRunsRepo:
    COLLECTION = "automation_runs"

    def __init__(self, db) -> None:
        self.coll = db[self.COLLECTION]

    async def create(self, run: AutomationRun) -> str:
        doc = model_to_doc(run)
        result = await self.coll.insert_one(doc)
        return str(result.inserted_id)

    async def get(self, run_id: str) -> AutomationRun | None:
        doc = await self.coll.find_one({"_id": ObjectId(run_id)})
        return doc_to_model(doc, AutomationRun, id_field="id") if doc else None

    async def update_running(
        self,
        run_id: str,
        *,
        started_at: datetime | None = None,
        whoop_summary: dict[str, Any] | None = None,
        habit_recompute_summary: list[dict[str, Any]] | None = None,
        render_summary: dict[str, Any] | None = None,
        remarkable_summary: dict[str, Any] | None = None,
    ) -> bool:
        update: dict[str, Any] = {"status": "running"}
        if started_at is not None:
            update["started_at"] = started_at
        if whoop_summary is not None:
            update["whoop_summary"] = whoop_summary
        if habit_recompute_summary is not None:
            update["habit_recompute_summary"] = habit_recompute_summary
        if render_summary is not None:
            update["render_summary"] = render_summary
        if remarkable_summary is not None:
            update["remarkable_summary"] = remarkable_summary
        result = await self.coll.update_one({"_id": ObjectId(run_id)}, {"$set": update})
        return result.modified_count > 0

    async def complete(
        self,
        run_id: str,
        *,
        finished_at: datetime,
        whoop_summary: dict[str, Any],
        habit_recompute_summary: list[dict[str, Any]],
        render_summary: dict[str, Any],
        remarkable_summary: dict[str, Any],
    ) -> bool:
        result = await self.coll.update_one(
            {"_id": ObjectId(run_id)},
            {
                "$set": {
                    "status": "completed",
                    "finished_at": finished_at,
                    "whoop_summary": whoop_summary,
                    "habit_recompute_summary": habit_recompute_summary,
                    "render_summary": render_summary,
                    "remarkable_summary": remarkable_summary,
                    "error": None,
                }
            },
        )
        return result.modified_count > 0

    async def fail(
        self,
        run_id: str,
        *,
        finished_at: datetime,
        error: str,
        whoop_summary: dict[str, Any] | None = None,
        habit_recompute_summary: list[dict[str, Any]] | None = None,
        render_summary: dict[str, Any] | None = None,
        remarkable_summary: dict[str, Any] | None = None,
    ) -> bool:
        update: dict[str, Any] = {
            "status": "failed",
            "finished_at": finished_at,
            "error": error,
        }
        if whoop_summary is not None:
            update["whoop_summary"] = whoop_summary
        if habit_recompute_summary is not None:
            update["habit_recompute_summary"] = habit_recompute_summary
        if render_summary is not None:
            update["render_summary"] = render_summary
        if remarkable_summary is not None:
            update["remarkable_summary"] = remarkable_summary
        result = await self.coll.update_one({"_id": ObjectId(run_id)}, {"$set": update})
        return result.modified_count > 0

    async def latest(self) -> AutomationRun | None:
        doc = await self.coll.find_one({}, sort=[("started_at", -1)])
        return doc_to_model(doc, AutomationRun, id_field="id") if doc else None

    async def list_recent(self, limit: int = 50) -> list[AutomationRun]:
        cursor = self.coll.find().sort("started_at", -1).limit(limit)
        return [doc_to_model(doc, AutomationRun, id_field="id") async for doc in cursor]
