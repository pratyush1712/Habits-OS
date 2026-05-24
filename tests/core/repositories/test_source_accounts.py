"""Integration tests for SourceAccountsRepo."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.core.models import SourceAccount
from packages.core.repositories import SourceAccountsRepo


def _account(**overrides):
    base = dict(
        source="whoop",
        external_user_id="user-123",
        display_name="Test User",
        scopes=["read:workout", "read:sleep"],
        encrypted_access_token=b"\x01\x02\x03cipher",
        encrypted_refresh_token=b"\x04\x05refresh",
        connected_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return SourceAccount(**base)


async def test_upsert_and_get_preserves_bytes_tokens(db):
    repo = SourceAccountsRepo(db)
    await repo.upsert(_account())

    got = await repo.get("whoop", "user-123")
    assert got is not None
    assert got.encrypted_access_token == b"\x01\x02\x03cipher"
    assert got.encrypted_refresh_token == b"\x04\x05refresh"
    assert got.scopes == ["read:workout", "read:sleep"]
    assert got.id == "whoop:user-123"


async def test_upsert_replaces(db):
    repo = SourceAccountsRepo(db)
    await repo.upsert(_account(display_name="Old"))
    await repo.upsert(_account(display_name="New"))

    got = await repo.get("whoop", "user-123")
    assert got is not None and got.display_name == "New"


async def test_list_by_source(db):
    repo = SourceAccountsRepo(db)
    await repo.upsert(_account(external_user_id="a"))
    await repo.upsert(_account(external_user_id="b"))
    await repo.upsert(_account(source="muse", external_user_id="m"))

    whoop = await repo.list_by_source("whoop")
    assert {a.external_user_id for a in whoop} == {"a", "b"}


async def test_mark_synced_and_webhook(db):
    repo = SourceAccountsRepo(db)
    await repo.upsert(_account())

    now = datetime(2026, 5, 24, 10, 0, tzinfo=timezone.utc)
    assert await repo.mark_synced("whoop", "user-123", now) is True
    assert await repo.mark_webhook("whoop", "user-123", now) is True

    got = await repo.get("whoop", "user-123")
    assert got is not None
    assert got.last_sync_at == now
    assert got.last_webhook_at == now
