"""Integration tests for RenderJobsRepo."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.core.models import RenderJob
from packages.core.repositories import RenderJobsRepo


async def test_create_returns_string_id(db):
    repo = RenderJobsRepo(db)
    job = RenderJob(month="2026-05", triggered_by="manual")
    job_id = await repo.create(job)
    assert isinstance(job_id, str) and len(job_id) == 24  # ObjectId hex length

    fetched = await repo.get(job_id)
    assert fetched is not None
    assert fetched.id == job_id
    assert fetched.month == "2026-05"
    assert fetched.status == "queued"


async def test_update_status_transitions(db):
    repo = RenderJobsRepo(db)
    job_id = await repo.create(RenderJob(month="2026-05"))

    started_at = datetime.now(timezone.utc)
    assert await repo.update_status(job_id, status="running", started_at=started_at)

    finished_at = datetime.now(timezone.utc)
    assert await repo.update_status(
        job_id,
        status="done",
        finished_at=finished_at,
        output_path="data/generated/2026-05-habit-dashboard.pdf",
    )

    job = await repo.get(job_id)
    assert job is not None
    assert job.status == "done"
    assert job.output_path == "data/generated/2026-05-habit-dashboard.pdf"
    assert job.started_at is not None and job.finished_at is not None


async def test_latest_for_month_picks_most_recent(db):
    repo = RenderJobsRepo(db)
    older = RenderJob(month="2026-05", requested_at=datetime(2026, 5, 1, tzinfo=timezone.utc))
    newer = RenderJob(month="2026-05", requested_at=datetime(2026, 5, 24, tzinfo=timezone.utc))
    await repo.create(older)
    newer_id = await repo.create(newer)

    latest = await repo.latest_for_month("2026-05")
    assert latest is not None and latest.id == newer_id


async def test_list_by_status(db):
    repo = RenderJobsRepo(db)
    await repo.create(RenderJob(month="2026-05", status="queued"))
    j2 = await repo.create(RenderJob(month="2026-05"))
    await repo.update_status(j2, status="done")

    done = await repo.list_by_status("done")
    assert len(done) == 1
    assert done[0].id == j2
