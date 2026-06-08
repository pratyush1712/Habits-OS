from __future__ import annotations


_DEFAULT_KEYS = {"workout", "medication", "meditation", "journaling", "sleep", "recovery"}


async def test_default_habit_seeding_and_listing(api_client):
    r = await api_client.get("/habits")
    assert r.status_code == 200
    habits = r.json()
    keys = {h["key"] for h in habits}
    assert keys == _DEFAULT_KEYS
    assert all(h["enabled"] for h in habits)
    # Sleep and recovery are computed but metric-only (not tracked cards);
    # the deliberate-action habits are not.
    by_key = {h["key"]: h for h in habits}
    assert by_key["sleep"]["metric_only"] is True
    assert by_key["recovery"]["metric_only"] is True
    assert by_key["workout"]["metric_only"] is False

    # Manual endpoint is idempotent and keeps active defaults available.
    seed = await api_client.post("/habits/seed-defaults")
    assert seed.status_code == 200
    payload = seed.json()
    assert payload["total_active"] == len(_DEFAULT_KEYS)
    assert payload["seeded"] >= 0




async def test_recompute_with_active_habits(api_client):
    imported = await api_client.post("/events/import-sample")
    assert imported.status_code == 200

    recompute = await api_client.post("/habits/recompute?month=2026-05")
    assert recompute.status_code == 200
    result = recompute.json()
    assert result["habits"] >= 5
    assert result["events"] > 0
    assert result["entries_written"] > 0
    assert result["warning"] is None


async def test_month_state_includes_active_habits(api_client):
    r = await api_client.get("/state/month?month=2030-01")
    assert r.status_code == 200
    state = r.json()
    assert state["entries"] == []
    keys = {h["key"] for h in state["habits"]}
    assert keys == _DEFAULT_KEYS
