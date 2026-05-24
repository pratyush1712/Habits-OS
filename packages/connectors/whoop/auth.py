"""OAuth helpers for WHOOP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode

import httpx

from packages.core.models import SourceAccount


@dataclass(frozen=True)
class WhoopOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...]
    auth_url: str = "https://api.prod.whoop.com/oauth/oauth2/auth"
    token_url: str = "https://api.prod.whoop.com/oauth/oauth2/token"


class WhoopOAuthError(RuntimeError):
    pass


def generate_state() -> str:
    """Generate an eight-character OAuth state value per WHOOP docs."""
    return token_urlsafe(8)[:8]


def build_authorization_url(config: WhoopOAuthConfig, state: str) -> str:
    query = urlencode(
        {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": state,
        }
    )
    return f"{config.auth_url}?{query}"


async def exchange_code_for_account(
    config: WhoopOAuthConfig,
    *,
    code: str,
    external_user_id: str,
    display_name: str = "WHOOP",
    client: httpx.AsyncClient | None = None,
) -> SourceAccount:
    token = await _post_token(
        config,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        },
        client=client,
    )
    return account_from_token_response(
        token,
        external_user_id=external_user_id,
        display_name=display_name,
        requested_scopes=config.scopes,
    )


async def refresh_account_tokens(
    config: WhoopOAuthConfig,
    account: SourceAccount,
    *,
    client: httpx.AsyncClient | None = None,
) -> SourceAccount:
    refresh_token = _decode_token(account.encrypted_refresh_token, "refresh")
    token = await _post_token(
        config,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "scope": " ".join(config.scopes),
        },
        client=client,
    )
    refreshed = account_from_token_response(
        token,
        external_user_id=account.external_user_id,
        display_name=account.display_name,
        requested_scopes=tuple(account.scopes or config.scopes),
    )
    return refreshed.model_copy(
        update={
            "id": account.id,
            "connected_at": account.connected_at,
            "last_sync_at": account.last_sync_at,
            "last_webhook_at": account.last_webhook_at,
            "status": "active",
        }
    )


def account_from_token_response(
    token: dict,
    *,
    external_user_id: str,
    display_name: str,
    requested_scopes: tuple[str, ...],
) -> SourceAccount:
    access = token.get("access_token")
    refresh = token.get("refresh_token")
    if not access:
        raise WhoopOAuthError("WHOOP token response missing access_token")
    scope_text = str(token.get("scope") or " ".join(requested_scopes))
    expires_in = token.get("expires_in")
    expires_at = None
    if expires_in is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    return SourceAccount(
        source="whoop",
        external_user_id=external_user_id,
        display_name=display_name,
        scopes=scope_text.split(),
        encrypted_access_token=str(access).encode("utf-8"),
        encrypted_refresh_token=str(refresh).encode("utf-8") if refresh else None,
        token_expires_at=expires_at,
        status="active",
    )


def access_token_from_account(account: SourceAccount) -> str:
    return _decode_token(account.encrypted_access_token, "access")


def token_needs_refresh(account: SourceAccount, *, skew_seconds: int = 60) -> bool:
    if account.token_expires_at is None:
        return False
    expires = account.token_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= datetime.now(timezone.utc) + timedelta(seconds=skew_seconds)


async def _post_token(
    config: WhoopOAuthConfig,
    data: dict[str, str],
    *,
    client: httpx.AsyncClient | None,
) -> dict:
    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=20)
    try:
        response = await active_client.post(config.token_url, data=data)
        if response.status_code >= 400:
            raise WhoopOAuthError(f"WHOOP token request failed: HTTP {response.status_code} {response.text}")
        return response.json()
    finally:
        if owns_client:
            await active_client.aclose()


def _decode_token(value: bytes | None, label: str) -> str:
    if not value:
        raise WhoopOAuthError(f"WHOOP account missing {label} token")
    return value.decode("utf-8")
