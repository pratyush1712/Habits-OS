"""Smoke tests for the connector contract in packages/connectors/base.py.

These are intentionally minimal — the contract is a documentation
artifact backed by Pydantic models and a structural Protocol. The tests
exist to lock down the public shape so future agents notice if they
break it accidentally.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from packages.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorCapability,
    IntegrationMetadata,
    IntegrationSyncSummary,
    SyncMode,
)
from packages.core.models import SourceEvent


def test_auth_type_values_are_stable() -> None:
    expected = {
        "oauth2",
        "api_key",
        "webhook_only",
        "local_file",
        "shortcut_bridge",
        "apple_health_bridge",
        "manual",
        "none",
    }
    assert {member.value for member in AuthType} == expected


def test_sync_mode_values_are_stable() -> None:
    expected = {
        "pull_range",
        "pull_incremental",
        "push_webhook",
        "import_file",
        "manual_endpoint",
    }
    assert {member.value for member in SyncMode} == expected


def test_connector_capability_round_trips() -> None:
    cap = ConnectorCapability(
        nightly_eligible=True,
        supports_date_range_sync=True,
        supports_backfill=True,
        supports_reconciliation=True,
        recommended_reconcile_window_days=14,
        service_revises_historical_data=True,
        sync_is_idempotent=True,
        required_env_vars=["WHOOP_CLIENT_ID"],
        graceful_when_unconfigured=True,
    )
    assert ConnectorCapability.model_validate(cap.model_dump()) == cap


def test_connector_capability_rejects_negative_reconcile_window() -> None:
    with pytest.raises(ValidationError):
        ConnectorCapability(
            nightly_eligible=False,
            supports_date_range_sync=False,
            supports_backfill=False,
            supports_reconciliation=False,
            recommended_reconcile_window_days=-1,
        )


def test_integration_metadata_round_trips() -> None:
    metadata = IntegrationMetadata(
        source="whoop",
        display_name="WHOOP",
        auth_type=AuthType.OAUTH2,
        sync_modes=[SyncMode.PULL_RANGE, SyncMode.PUSH_WEBHOOK],
        capabilities=ConnectorCapability(
            nightly_eligible=True,
            supports_date_range_sync=True,
            supports_backfill=True,
            supports_reconciliation=True,
        ),
        docs_path="docs/whoop_integration.md",
    )
    assert IntegrationMetadata.model_validate(metadata.model_dump()) == metadata


def test_integration_sync_summary_defaults() -> None:
    summary = IntegrationSyncSummary(
        source="whoop",
        account_id="user-1",
        start=date(2026, 5, 1),
        end=date(2026, 5, 14),
    )
    assert summary.event_counts_by_type == {}
    assert summary.inserted == 0
    assert summary.updated == 0
    assert summary.affected_months == []
    assert summary.errors == []
    assert summary.warnings == []
    assert summary.skipped_reason is None


def test_integration_sync_summary_can_express_skipped_run() -> None:
    summary = IntegrationSyncSummary(
        source="muse",
        account_id=None,
        start=date(2026, 5, 1),
        end=date(2026, 5, 14),
        skipped_reason="missing_credentials",
    )
    assert summary.skipped_reason == "missing_credentials"


def test_integration_sync_summary_rejects_unknown_source() -> None:
    with pytest.raises(ValidationError):
        IntegrationSyncSummary(
            source="not_a_real_source",  # type: ignore[arg-type]
            start=date(2026, 5, 1),
            end=date(2026, 5, 14),
        )


def test_base_connector_is_runtime_checkable_against_minimal_impl() -> None:
    """A minimal conforming class should satisfy the structural Protocol."""

    class _Stub:
        def metadata(self) -> IntegrationMetadata:
            return IntegrationMetadata(
                source="manual",
                display_name="Stub",
                auth_type=AuthType.MANUAL,
                sync_modes=[SyncMode.MANUAL_ENDPOINT],
                capabilities=ConnectorCapability(
                    nightly_eligible=False,
                    supports_date_range_sync=False,
                    supports_backfill=False,
                    supports_reconciliation=False,
                ),
            )

        async def sync_range(
            self,
            *,
            account_id: str,
            start: date,
            end: date,
            recompute: bool = False,
        ) -> IntegrationSyncSummary:
            return IntegrationSyncSummary(
                source="manual",
                account_id=account_id,
                start=start,
                end=end,
                skipped_reason="stub",
            )

        def normalize(self, payload: dict) -> SourceEvent:
            return SourceEvent(
                id="manual:1",
                source="manual",
                source_event_id="1",
                event_type="manual",
                start_time_utc=datetime(2026, 5, 1, tzinfo=timezone.utc),
                local_date=date(2026, 5, 1),
            )

    assert isinstance(_Stub(), BaseConnector)
