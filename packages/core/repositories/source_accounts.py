"""Repository for OAuth-connected source accounts (WHOOP, Muse, ...).

Token bytes are persisted as BSON BinData. Encryption-at-rest is intentionally
not implemented yet — see CLAUDE.md §10 and docs/persistence.md.
"""

from __future__ import annotations

from datetime import datetime

from packages.core.models import EventSource, SourceAccount
from packages.core.repositories.base import doc_to_model, model_to_doc


def _account_id(source: str, external_user_id: str) -> str:
    return f"{source}:{external_user_id}"


class SourceAccountsRepo:
    COLLECTION = "source_accounts"

    def __init__(self, db) -> None:
        self.coll = db[self.COLLECTION]

    async def upsert(self, account: SourceAccount) -> None:
        doc = model_to_doc(account)
        doc["_id"] = _account_id(account.source, account.external_user_id)
        await self.coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    async def get(self, source: EventSource, external_user_id: str) -> SourceAccount | None:
        doc = await self.coll.find_one({"_id": _account_id(source, external_user_id)})
        return doc_to_model(doc, SourceAccount, id_field="id") if doc else None

    async def list_by_source(self, source: EventSource) -> list[SourceAccount]:
        cursor = self.coll.find({"source": source})
        return [doc_to_model(d, SourceAccount, id_field="id") async for d in cursor]

    async def mark_synced(
        self, source: EventSource, external_user_id: str, at: datetime
    ) -> bool:
        result = await self.coll.update_one(
            {"_id": _account_id(source, external_user_id)},
            {"$set": {"last_sync_at": at}},
        )
        return result.modified_count > 0

    async def mark_webhook(
        self, source: EventSource, external_user_id: str, at: datetime
    ) -> bool:
        result = await self.coll.update_one(
            {"_id": _account_id(source, external_user_id)},
            {"$set": {"last_webhook_at": at}},
        )
        return result.modified_count > 0
