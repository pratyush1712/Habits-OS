from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apps.api.deps import get_whoop_sync_service
from apps.api.routes.whoop import router
from apps.api.services.whoop_sync import WhoopAuthorization
from packages.core.models import SourceAccount


class FakeWhoopSyncService:
    def __init__(self) -> None:
        self.codes: list[str] = []

    def authorization(self) -> WhoopAuthorization:
        return WhoopAuthorization(
            authorization_url="https://example.test/oauth",
            state="abcd1234",
            scopes=["offline", "read:workout"],
        )

    async def complete_oauth(self, code: str) -> SourceAccount:
        self.codes.append(code)
        return SourceAccount(
            source="whoop",
            external_user_id="whoop-user-1",
            display_name="WHOOP User",
            status="active",
            connected_at=datetime.now(timezone.utc),
        )


@pytest.mark.asyncio
async def test_oauth_callback_validates_state() -> None:
    app = FastAPI()
    app.include_router(router)
    fake = FakeWhoopSyncService()
    app.dependency_overrides[get_whoop_sync_service] = lambda: fake

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.get("/whoop/oauth/start")
        assert start.status_code == 200
        state = start.json()["state"]
        assert state == "abcd1234"

        missing_state = await client.get("/whoop/oauth/callback?code=test-code")
        assert missing_state.status_code == 422

        invalid_state = await client.get("/whoop/oauth/callback?code=test-code&state=wrong")
        assert invalid_state.status_code == 400
        assert invalid_state.json()["detail"] == "invalid oauth state"

        valid_state = await client.get(f"/whoop/oauth/callback?code=test-code&state={state}")
        assert valid_state.status_code == 200
        assert fake.codes == ["test-code"]

        replay = await client.get(f"/whoop/oauth/callback?code=test-code-2&state={state}")
        assert replay.status_code == 400
        assert replay.json()["detail"] == "invalid oauth state"
