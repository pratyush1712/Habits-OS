from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from packages.connectors.whoop.client import WhoopClient, WhoopRateLimitError


@pytest.mark.asyncio
async def test_collection_paginates_with_next_token():
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if request.url.params.get("nextToken") == "next-page":
            return httpx.Response(200, json={"records": [{"id": "b"}]})
        return httpx.Response(
            200,
            json={"records": [{"id": "a"}], "next_token": "next-page"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = WhoopClient(
            access_token="token",
            base_url="https://example.test/developer",
            http_client=http_client,
        )
        records = await client.list_workouts(
            start=datetime(2026, 5, 1, tzinfo=timezone.utc),
            end=datetime(2026, 5, 2, tzinfo=timezone.utc),
        )

    assert records == [{"id": "a"}, {"id": "b"}]
    assert "limit=25" in seen_urls[0]
    assert "start=2026-05-01T00%3A00%3A00Z" in seen_urls[0]
    assert "nextToken=next-page" in seen_urls[1]


@pytest.mark.asyncio
async def test_rate_limit_error_exposes_reset_header():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            429,
            headers={"X-RateLimit-Reset": "7"},
            json={"error": "limited"},
        )
    )
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = WhoopClient(
            access_token="token",
            base_url="https://example.test/developer",
            http_client=http_client,
        )
        with pytest.raises(WhoopRateLimitError) as exc:
            await client.get_profile_basic()

    assert exc.value.reset_seconds == 7
