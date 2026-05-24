"""WHOOP synchronization service.

This service is the boundary between WHOOP connector modules and HabitOS
persistence. Connector modules do HTTP/normalization; repositories remain the
only code that touches MongoDB.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import TypedDict

import httpx

from apps.api.config import WhoopSettings
from apps.api.services.habit_evaluation import HabitEvaluationService
from packages.connectors.whoop.auth import (
    WhoopOAuthConfig,
    access_token_from_account,
    account_from_token_response,
    build_authorization_url,
    generate_state,
    refresh_account_tokens,
    token_needs_refresh,
)
from packages.connectors.whoop.client import WhoopApiError, WhoopClient
from packages.connectors.whoop.normalizer import (
    normalize_recovery,
    normalize_sleep,
    normalize_workout,
)
from packages.core.models import SourceAccount, SourceEvent
from packages.core.repositories import SourceAccountsRepo, SourceEventsRepo


class WhoopSyncResult(TypedDict):
    external_user_id: str
    start: str
    end: str
    workouts: int
    sleeps: int
    recoveries: int
    events_written: int
    recomputed_months: list[str]
    written: dict[str, dict[str, int]]


@dataclass(frozen=True)
class WhoopAuthorization:
    authorization_url: str
    state: str
    scopes: list[str]


class WhoopSyncService:
    def __init__(
        self,
        settings: WhoopSettings,
        accounts_repo: SourceAccountsRepo,
        events_repo: SourceEventsRepo,
        evaluation: HabitEvaluationService,
    ) -> None:
        self.settings = settings
        self.accounts_repo = accounts_repo
        self.events_repo = events_repo
        self.evaluation = evaluation

    def authorization(self) -> WhoopAuthorization:
        config = self._oauth_config()
        state = generate_state()
        return WhoopAuthorization(
            authorization_url=build_authorization_url(config, state),
            state=state,
            scopes=list(config.scopes),
        )

    async def complete_oauth(self, code: str) -> SourceAccount:
        config = self._oauth_config()
        async with httpx.AsyncClient(timeout=30) as http_client:
            token_response = await _exchange_code(config, code, http_client)
            access_token = str(token_response["access_token"])
            profile = await WhoopClient(
                access_token=access_token,
                base_url=self.settings.api_base_url,
                http_client=http_client,
            ).get_profile_basic()

        external_user_id = str(profile["user_id"])
        display_name = _display_name(profile)
        account = account_from_token_response(
            token_response,
            external_user_id=external_user_id,
            display_name=display_name,
            requested_scopes=config.scopes,
        )
        await self.accounts_repo.upsert(account)
        stored = await self.accounts_repo.get("whoop", external_user_id)
        return stored or account

    async def status(self) -> dict:
        accounts = await self.accounts_repo.list_by_source("whoop")
        return {
            "configured": bool(self.settings.client_id and self.settings.client_secret),
            "accounts": [_account_status(account) for account in accounts],
        }

    async def sync_range(
        self,
        *,
        external_user_id: str,
        start: date,
        end: date,
        recompute: bool = True,
    ) -> WhoopSyncResult:
        account = await self.accounts_repo.get("whoop", external_user_id)
        if account is None:
            raise ValueError(f"No active WHOOP account found for {external_user_id!r}")
        if account.status != "active":
            raise ValueError(f"WHOOP account {external_user_id!r} is {account.status}")

        account = await self._fresh_account(account)
        access_token = access_token_from_account(account)
        start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
        # Public API date ranges are inclusive; WHOOP's query end is exclusive.
        end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)

        async with httpx.AsyncClient(timeout=30) as http_client:
            client = WhoopClient(
                access_token=access_token,
                base_url=self.settings.api_base_url,
                http_client=http_client,
            )
            workouts = await client.list_workouts(start=start_dt, end=end_dt)
            sleeps = await client.list_sleeps(start=start_dt, end=end_dt)
            recoveries = await client.list_recoveries(start=start_dt, end=end_dt)

        sleep_by_id = {str(s.get("id")): s for s in sleeps if s.get("id")}
        workout_events: list[SourceEvent] = [normalize_workout(w) for w in workouts]
        sleep_events: list[SourceEvent] = [normalize_sleep(s) for s in sleeps]
        recovery_events: list[SourceEvent] = [
            normalize_recovery(r, sleep_payload=sleep_by_id.get(str(r.get("sleep_id"))))
            for r in recoveries
        ]
        events = [*workout_events, *sleep_events, *recovery_events]

        workout_written = await self.events_repo.upsert_many_counts(workout_events)
        sleep_written = await self.events_repo.upsert_many_counts(sleep_events)
        recovery_written = await self.events_repo.upsert_many_counts(recovery_events)
        written = workout_written["total"] + sleep_written["total"] + recovery_written["total"]
        await self.accounts_repo.mark_synced("whoop", external_user_id, datetime.now(timezone.utc))

        recomputed_months: list[str] = []
        if recompute:
            for month in sorted({event.local_date.strftime("%Y-%m") for event in events}):
                await self.evaluation.recompute(month)
                recomputed_months.append(month)

        return {
            "external_user_id": external_user_id,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "workouts": len(workouts),
            "sleeps": len(sleeps),
            "recoveries": len(recoveries),
            "events_written": written,
            "recomputed_months": recomputed_months,
            "written": {
                "workouts": _counts_for_response(workout_written),
                "sleeps": _counts_for_response(sleep_written),
                "recoveries": _counts_for_response(recovery_written),
            },
        }

    async def _fresh_account(self, account: SourceAccount) -> SourceAccount:
        if not token_needs_refresh(account):
            return account
        refreshed = await refresh_account_tokens(self._oauth_config(), account)
        await self.accounts_repo.upsert(refreshed)
        stored = await self.accounts_repo.get("whoop", refreshed.external_user_id)
        return stored or refreshed

    def _oauth_config(self) -> WhoopOAuthConfig:
        if not self.settings.client_id or not self.settings.client_secret:
            raise ValueError("WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET are required")
        return WhoopOAuthConfig(
            client_id=self.settings.client_id,
            client_secret=self.settings.client_secret,
            redirect_uri=self.settings.redirect_uri,
            scopes=tuple(self.settings.scopes),
            auth_url=self.settings.auth_url,
            token_url=self.settings.token_url,
        )


async def _exchange_code(
    config: WhoopOAuthConfig,
    code: str,
    http_client: httpx.AsyncClient,
) -> dict:
    response = await http_client.post(
        config.token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        },
    )
    if response.status_code >= 400:
        raise WhoopApiError(
            f"WHOOP token exchange failed: HTTP {response.status_code} {response.text}",
            status_code=response.status_code,
        )
    data = response.json()
    if not isinstance(data, dict) or not data.get("access_token"):
        raise WhoopApiError("WHOOP token exchange returned an invalid payload")
    return data


def _display_name(profile: dict) -> str:
    first = profile.get("first_name")
    last = profile.get("last_name")
    full = " ".join(str(p) for p in [first, last] if p)
    return full or str(profile.get("email") or "WHOOP")


def _counts_for_response(counts: dict[str, int]) -> dict[str, int]:
    return {"inserted": counts["inserted"], "updated": counts["updated"]}


def _account_status(account: SourceAccount) -> dict:
    return {
        "external_user_id": account.external_user_id,
        "display_name": account.display_name,
        "status": account.status,
        "connected_at": account.connected_at.isoformat(),
        "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
        "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
        "scopes": account.scopes,
    }
