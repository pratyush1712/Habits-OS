"""Async WHOOP API client.

The client is deliberately storage-agnostic: it accepts an access token and
returns raw API payloads. Token lookup/refresh and persistence live in services.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


class WhoopApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WhoopRateLimitError(WhoopApiError):
    def __init__(self, reset_seconds: int | None = None) -> None:
        super().__init__("WHOOP rate limit exceeded", status_code=429)
        self.reset_seconds = reset_seconds


class WhoopClient:
    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = "https://api.prod.whoop.com/developer",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self._client = http_client

    async def get_profile_basic(self) -> dict[str, Any]:
        return await self._get_json("/v2/user/profile/basic")

    async def list_workouts(self, *, start: datetime, end: datetime) -> list[dict[str, Any]]:
        return await self._get_collection("/v2/activity/workout", start=start, end=end)

    async def get_workout(self, workout_id: str) -> dict[str, Any]:
        return await self._get_json(f"/v2/activity/workout/{workout_id}")

    async def list_sleeps(self, *, start: datetime, end: datetime) -> list[dict[str, Any]]:
        return await self._get_collection("/v2/activity/sleep", start=start, end=end)

    async def get_sleep(self, sleep_id: str) -> dict[str, Any]:
        return await self._get_json(f"/v2/activity/sleep/{sleep_id}")

    async def list_recoveries(self, *, start: datetime, end: datetime) -> list[dict[str, Any]]:
        return await self._get_collection("/v2/recovery", start=start, end=end)

    async def get_recovery_for_cycle(self, cycle_id: int | str) -> dict[str, Any]:
        return await self._get_json(f"/v2/cycle/{cycle_id}/recovery")

    async def _get_collection(
        self,
        path: str,
        *,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        next_token: str | None = None
        while True:
            params = {
                "limit": 25,
                "start": _format_datetime(start),
                "end": _format_datetime(end),
            }
            if next_token:
                params["nextToken"] = next_token
            payload = await self._get_json(path, params=params)
            page_records = payload.get("records", [])
            if not isinstance(page_records, list):
                raise WhoopApiError("WHOOP collection response records was not a list")
            records.extend(page_records)
            next_token = payload.get("next_token")
            if not next_token:
                return records

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30)
        try:
            response = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if response.status_code == 429:
                reset = response.headers.get("X-RateLimit-Reset")
                raise WhoopRateLimitError(int(reset) if reset and reset.isdigit() else None)
            if response.status_code == 401:
                raise WhoopApiError("WHOOP access token unauthorized", status_code=401)
            if response.status_code >= 400:
                raise WhoopApiError(
                    f"WHOOP API request failed: HTTP {response.status_code} {response.text}",
                    status_code=response.status_code,
                )
            data = response.json()
            if not isinstance(data, dict):
                raise WhoopApiError("WHOOP API response was not an object")
            return data
        finally:
            if owns_client:
                await client.aclose()


def _format_datetime(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
