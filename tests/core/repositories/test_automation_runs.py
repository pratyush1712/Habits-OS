"""Unit tests for AutomationRunsRepo."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from packages.core.models import AutomationRun
from packages.core.repositories.automation_runs import AutomationRunsRepo


def _run(**overrides) -> AutomationRun:
    base = dict(
        run_type="nightly",
        status="running",
        dry_run=True,
        timezone="UTC",
        date="2026-06-01",
        window={"start": "2026-05-18", "end": "2026-06-01", "reconcile_days": 14},
        months={"current": "2026-06", "previous": "2026-05", "affected": ["2026-05", "2026-06"]},
        whoop_summary={"status": "pending"},
        habit_recompute_summary=[],
        render_summary={"current": {"status": "pending"}},
        remarkable_summary={"status": "pending"},
    )
    base.update(overrides)
    return AutomationRun(**base)


class _InsertOneResult:
    def __init__(self, inserted_id: ObjectId) -> None:
        self.inserted_id = inserted_id


class _UpdateResult:
    def __init__(self, modified_count: int) -> None:
        self.modified_count = modified_count


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs

    def sort(self, field: str, direction: int):
        reverse = direction < 0
        self.docs = sorted(self.docs, key=lambda doc: doc[field], reverse=reverse)
        return self

    def limit(self, limit: int):
        self.docs = self.docs[:limit]
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.docs):
            raise StopAsyncIteration
        doc = self.docs[self._index]
        self._index += 1
        return doc


class _Collection:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    async def insert_one(self, doc: dict):
        stored = dict(doc)
        stored["_id"] = ObjectId()
        self.docs.append(stored)
        return _InsertOneResult(stored["_id"])

    async def find_one(self, query: dict, sort: list[tuple[str, int]] | None = None):
        docs = list(self.docs)
        if "_id" in query:
            docs = [doc for doc in docs if doc["_id"] == query["_id"]]
        if sort:
            field, direction = sort[0]
            reverse = direction < 0
            docs = sorted(docs, key=lambda doc: doc[field], reverse=reverse)
        return docs[0] if docs else None

    async def update_one(self, query: dict, update: dict):
        for doc in self.docs:
            if doc["_id"] == query["_id"]:
                doc.update(update["$set"])
                return _UpdateResult(1)
        return _UpdateResult(0)

    def find(self):
        return _Cursor(list(self.docs))


class _Db:
    def __init__(self) -> None:
        self.collections: dict[str, _Collection] = {}

    def __getitem__(self, name: str) -> _Collection:
        self.collections.setdefault(name, _Collection())
        return self.collections[name]


async def test_create_and_get_round_trip():
    repo = AutomationRunsRepo(_Db())
    run_id = await repo.create(_run())

    got = await repo.get(run_id)
    assert got is not None
    assert got.id == run_id
    assert got.run_type == "nightly"
    assert got.status == "running"


async def test_complete_updates_run():
    repo = AutomationRunsRepo(_Db())
    run_id = await repo.create(_run())
    finished_at = datetime(2026, 6, 1, 7, 5, tzinfo=timezone.utc)

    assert await repo.complete(
        run_id,
        finished_at=finished_at,
        whoop_summary={"events_written": 3},
        habit_recompute_summary=[{"month": "2026-06", "entries_written": 30}],
        render_summary={"current": {"status": "completed"}},
        remarkable_summary={"status": "manual_required"},
    )

    got = await repo.get(run_id)
    assert got is not None
    assert got.status == "completed"
    assert got.finished_at == finished_at
    assert got.render_summary["current"]["status"] == "completed"


async def test_fail_updates_run():
    repo = AutomationRunsRepo(_Db())
    run_id = await repo.create(_run())
    finished_at = datetime(2026, 6, 1, 7, 5, tzinfo=timezone.utc)

    assert await repo.fail(
        run_id,
        finished_at=finished_at,
        error="RuntimeError: whoop unavailable",
        remarkable_summary={"status": "skipped"},
    )

    got = await repo.get(run_id)
    assert got is not None
    assert got.status == "failed"
    assert got.error == "RuntimeError: whoop unavailable"
    assert got.remarkable_summary["status"] == "skipped"


async def test_latest_returns_most_recent_run():
    repo = AutomationRunsRepo(_Db())
    await repo.create(_run(started_at=datetime(2026, 6, 1, 7, 0, tzinfo=timezone.utc)))
    latest_id = await repo.create(
        _run(
            run_type="manual",
            started_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
        )
    )

    latest = await repo.latest()
    assert latest is not None
    assert latest.id == latest_id
