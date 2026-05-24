"""Local control-surface status summaries."""

from __future__ import annotations

from apps.api.config import Settings
from packages.core.repositories import RenderJobsRepo, SourceAccountsRepo


class StatusService:
    def __init__(
        self,
        db,
        settings: Settings,
        accounts_repo: SourceAccountsRepo,
        jobs_repo: RenderJobsRepo,
    ) -> None:
        self.db = db
        self.settings = settings
        self.accounts_repo = accounts_repo
        self.jobs_repo = jobs_repo

    async def status(self) -> dict:
        mongo = await self.mongo_status()
        return {
            "status": "ok" if mongo["connected"] else "degraded",
            "mongo": mongo,
            "integrations": await self.integrations_status(),
            "latest_render_job": _model_dump_or_none(await self.jobs_repo.latest()),
            "latest_sync": await self.latest_sync_status(),
        }

    async def mongo_status(self) -> dict:
        try:
            await self.db.command("ping")
        except Exception as e:
            return {"connected": False, "error": str(e)}
        return {
            "connected": True,
            "database": self.settings.mongodb_db_name,
        }

    async def integrations_status(self) -> dict:
        whoop_accounts = await self.accounts_repo.list_by_source("whoop")
        return {
            "whoop": {
                "configured": bool(
                    self.settings.whoop.client_id and self.settings.whoop.client_secret
                ),
                "connected_accounts": len(whoop_accounts),
                "scopes": list(self.settings.whoop.scopes),
            },
            "remarkable": {
                "configured": True,
                "adapter": "manual",
                "mode": "manual_upload",
                "machine_owned_root": "HabitOS",
            },
        }

    async def latest_sync_status(self) -> dict:
        whoop_accounts = await self.accounts_repo.list_by_source("whoop")
        latest_whoop = max(
            whoop_accounts,
            key=lambda account: account.last_sync_at or account.connected_at,
            default=None,
        )
        return {
            "whoop": _account_status(latest_whoop),
            "remarkable": {
                "adapter": "manual",
                "last_upload_status": "not_persisted",
                "note": "Manual upload attempts are not persisted yet; inspect latest render job.",
            },
        }


def _account_status(account) -> dict:
    if account is None:
        return {"connected": False, "last_sync_at": None, "status": "not_connected"}
    return {
        "connected": account.status == "active",
        "external_user_id": account.external_user_id,
        "display_name": account.display_name,
        "status": account.status,
        "connected_at": account.connected_at.isoformat(),
        "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
        "token_expires_at": (
            account.token_expires_at.isoformat() if account.token_expires_at else None
        ),
        "scopes": account.scopes,
    }


def _model_dump_or_none(model) -> dict | None:
    if model is None:
        return None
    return model.model_dump(mode="json")
