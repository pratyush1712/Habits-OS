"""End-to-end pipeline test: sample → Mongo → engine → state → PDF.

This is the M3 acceptance test. It exercises every required route and
verifies the chain that the user actually cares about.
"""

from __future__ import annotations

from pathlib import Path


MONTH = "2026-05"


async def test_full_pipeline(api_client):
    # 1) Ingest the committed sample events file into Mongo.
    r = await api_client.post("/events/import-sample")
    assert r.status_code == 200, r.text
    ingested = r.json()
    assert ingested["month"] == MONTH
    assert ingested["events"] > 0
    assert ingested["habits"] >= 5
    assert ingested["overrides"] >= 1

    # 2) GET /events filters by month.
    r = await api_client.get(f"/events?month={MONTH}")
    assert r.status_code == 200
    events = r.json()
    assert len(events) == ingested["events"]
    assert all(e["local_date"].startswith(MONTH) for e in events)

    # Source filter narrows the set further.
    r = await api_client.get(f"/events?month={MONTH}&source=whoop")
    assert r.status_code == 200
    assert all(e["source"] == "whoop" for e in r.json())

    # 3) Recompute writes habit_entries.
    r = await api_client.post(f"/habits/recompute?month={MONTH}")
    assert r.status_code == 200, r.text
    summary = r.json()
    assert summary["entries_written"] > 0
    written = summary["entries_written"]

    # 4) GET /habit-entries returns the written entries.
    r = await api_client.get(f"/habit-entries?month={MONTH}")
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) == written
    statuses = {e["status"] for e in entries}
    assert "checked" in statuses
    # The sample includes a manual override that wins over a computed entry.
    assert any(e["manually_overridden"] for e in entries)

    # 5) Re-running recompute is idempotent (delete-and-rewrite).
    r2 = await api_client.post(f"/habits/recompute?month={MONTH}")
    assert r2.status_code == 200
    assert r2.json()["entries_written"] == written
    assert r2.json()["entries_deleted"] == written

    # 6) /state/month derives a MonthHabitState — never stored as a snapshot.
    r = await api_client.get(f"/state/month?month={MONTH}")
    assert r.status_code == 200
    state = r.json()
    assert state["month"] == MONTH
    assert len(state["habits"]) >= 5
    assert len(state["entries"]) == written
    # generated_at is set by the model default at read time, proving derivation.
    assert state["generated_at"] is not None

    # 7) Render a PDF. The job moves pending → running → completed.
    r = await api_client.post(f"/render/month?month={MONTH}")
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["status"] == "completed"
    assert job["month"] == MONTH
    assert job["output_path"].endswith(f"{MONTH}-habit-dashboard.pdf")
    assert Path(job["output_path"]).exists()

    # 8) /render/latest reflects the newest job.
    r = await api_client.get("/render/latest")
    assert r.status_code == 200
    assert r.json()["id"] == job["id"]
    r = await api_client.get(f"/render/latest?month={MONTH}")
    assert r.status_code == 200
    assert r.json()["id"] == job["id"]

    # 9) /render/jobs lists the audit trail with the newest first.
    r = await api_client.get("/render/jobs")
    assert r.status_code == 200
    jobs = r.json()
    assert len(jobs) >= 1
    assert jobs[0]["id"] == job["id"]


async def test_state_for_empty_month_is_well_formed(api_client):
    """A month with no entries should still return a valid MonthHabitState."""
    r = await api_client.get("/state/month?month=2030-01")
    assert r.status_code == 200
    state = r.json()
    assert state["month"] == "2030-01"
    assert state["entries"] == []


async def test_latest_404_when_no_renders(api_client):
    r = await api_client.get("/render/latest")
    assert r.status_code == 404
