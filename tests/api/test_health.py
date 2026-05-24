"""Health check sanity test."""

from __future__ import annotations


async def test_health_ok(api_client):
    r = await api_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mongo"] == "connected"


async def test_missing_month_returns_422(api_client):
    """Pydantic should reject a malformed month query param."""
    r = await api_client.get("/habit-entries?month=not-a-month")
    assert r.status_code == 422

    r = await api_client.get("/state/month?month=2026/05")
    assert r.status_code == 422
