from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from packages.connectors.whoop.auth import (
    WhoopOAuthConfig,
    account_from_token_response,
    build_authorization_url,
    generate_state,
    token_needs_refresh,
)


def test_generate_state_is_eight_characters():
    assert len(generate_state()) == 8


def test_build_authorization_url_contains_required_oauth_params():
    config = WhoopOAuthConfig(
        client_id="client",
        client_secret="secret",
        redirect_uri="http://localhost/callback",
        scopes=("offline", "read:workout"),
    )

    url = build_authorization_url(config, "abcdefgh")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert params["client_id"] == ["client"]
    assert params["redirect_uri"] == ["http://localhost/callback"]
    assert params["response_type"] == ["code"]
    assert params["scope"] == ["offline read:workout"]
    assert params["state"] == ["abcdefgh"]


def test_account_from_token_response_stores_token_bytes_and_expiry():
    account = account_from_token_response(
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
            "scope": "offline read:workout",
        },
        external_user_id="123",
        display_name="Test User",
        requested_scopes=("offline",),
    )

    assert account.source == "whoop"
    assert account.external_user_id == "123"
    assert account.display_name == "Test User"
    assert account.encrypted_access_token == b"access"
    assert account.encrypted_refresh_token == b"refresh"
    assert account.scopes == ["offline", "read:workout"]
    assert account.token_expires_at is not None


def test_token_needs_refresh_with_skew():
    account = account_from_token_response(
        {"access_token": "access", "expires_in": 1},
        external_user_id="123",
        display_name="Test User",
        requested_scopes=("read:workout",),
    )

    assert token_needs_refresh(account, skew_seconds=60) is True


def test_token_without_expiry_does_not_force_refresh():
    account = account_from_token_response(
        {"access_token": "access"},
        external_user_id="123",
        display_name="Test User",
        requested_scopes=("read:workout",),
    )
    assert account.token_expires_at is None
    assert token_needs_refresh(account) is False
