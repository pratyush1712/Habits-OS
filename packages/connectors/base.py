"""Connector contract for HabitOS integrations.

This module is the formal, forward-looking integration contract. It is
additive only: WHOOP predates it and is not migrated yet. New connectors
should implement these shapes from day one.

What is here:

- ``AuthType``      — how an integration authenticates
- ``SyncMode``      — how data flows in (pull, push, manual, ...)
- ``ConnectorCapability`` — declarative capability flags an integration exposes
- ``IntegrationMetadata`` — self-description for a connector
- ``IntegrationSyncSummary`` — the typed return value from ``sync_range``
- ``BaseConnector``  — a structural ``Protocol`` for service-layer connectors

What is NOT here:

- No HTTP. No MongoDB. No FastAPI wiring. Connector implementations live in
  ``packages/connectors/<service>/`` and their service layer in
  ``apps/api/services/<service>_sync.py``.
- No runtime registry. The registry pattern is documented in
  ``docs/integration_blueprint.md`` and will be introduced once there are
  three or more automated integrations.
- No enforcement. ``BaseConnector`` is a structural ``Protocol``; conformance
  is contractual, checked through code review and the integration template
  checklist.

See ``docs/integration_blueprint.md`` for the full philosophy and the
Automation Compatibility Contract.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from packages.core.models import EventSource, SourceEvent


class AuthType(str, Enum):
    """How an integration authenticates its API calls."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    WEBHOOK_ONLY = "webhook_only"
    LOCAL_FILE = "local_file"
    SHORTCUT_BRIDGE = "shortcut_bridge"
    APPLE_HEALTH_BRIDGE = "apple_health_bridge"
    MANUAL = "manual"
    NONE = "none"


class SyncMode(str, Enum):
    """How records arrive in HabitOS for this integration."""

    PULL_RANGE = "pull_range"
    PULL_INCREMENTAL = "pull_incremental"
    PUSH_WEBHOOK = "push_webhook"
    IMPORT_FILE = "import_file"
    MANUAL_ENDPOINT = "manual_endpoint"


class ConnectorCapability(BaseModel):
    """Declarative capability flags every automated integration must report.

    These are read by ``AutomationService`` (today: implicitly per
    integration; tomorrow: through the future ``IntegrationRegistry``) to
    decide what to schedule, what to surface in ``/automation/status``, and
    how to behave when credentials are missing.

    Field semantics match the Automation Compatibility Contract in
    ``docs/integration_blueprint.md`` §Automation Compatibility Contract.
    """

    model_config = ConfigDict(extra="forbid")

    nightly_eligible: bool
    supports_date_range_sync: bool
    supports_backfill: bool
    supports_reconciliation: bool
    recommended_reconcile_window_days: int = Field(ge=0, default=14)
    service_revises_historical_data: bool = False
    sync_is_idempotent: bool = True
    required_env_vars: list[str] = Field(default_factory=list)
    graceful_when_unconfigured: bool = True


class IntegrationMetadata(BaseModel):
    """Self-description of a connector. Used by docs, /status, and registry."""

    model_config = ConfigDict(extra="forbid")

    source: EventSource
    display_name: str
    auth_type: AuthType
    sync_modes: list[SyncMode]
    capabilities: ConnectorCapability
    docs_path: str = ""


class IntegrationSyncSummary(BaseModel):
    """Result of one ``sync_range`` invocation. Returned to AutomationService.

    Every automated integration must produce a value-equivalent of this.
    WHOOP's ``WhoopSyncResult`` TypedDict predates this model and is
    convertible; the blueprint documents the migration path.

    Conventions:

    - ``event_counts_by_type`` keys are ``EventType`` literals (e.g.
      ``"workout"``, ``"sleep"``).
    - ``affected_months`` are ``YYYY-MM`` strings, in ascending order.
    - ``skipped_reason`` is set when the integration declined to run
      (missing credentials, disabled flag, etc.). When set, count fields
      should be zero and ``errors`` should be empty.
    - ``errors`` are conditions that should fail the run; ``warnings`` are
      conditions that should be surfaced but not abort.
    """

    model_config = ConfigDict(extra="forbid")

    source: EventSource
    account_id: str | None = None
    start: date
    end: date
    event_counts_by_type: dict[str, int] = Field(default_factory=dict)
    inserted: int = 0
    updated: int = 0
    affected_months: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    skipped_reason: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class BaseConnector(Protocol):
    """Structural contract for a HabitOS connector service.

    This is a ``Protocol``, not an abstract base class. New service-layer
    connectors should implement this shape; existing ones (WHOOP) predate it
    and may be migrated later.

    Methods:

    - ``metadata()`` — return ``IntegrationMetadata`` describing the
      connector. Pure; safe to call without credentials.
    - ``sync_range(account_id, start, end, recompute)`` — pull or import
      records for the given window, normalize them into ``SourceEvent``,
      upsert via the source-events repository, and return a typed summary.
      Must be idempotent.
    - ``normalize(payload)`` — pure mapping from a single raw service
      record to a ``SourceEvent``. No I/O. May raise ``ValueError`` if the
      payload is structurally invalid.

    A connector that cannot meaningfully implement ``sync_range`` (e.g. a
    pure webhook-push integration with no backfill API) should still expose
    it and either:

    - return an ``IntegrationSyncSummary`` with ``skipped_reason`` set, or
    - raise ``NotImplementedError`` — in which case ``capabilities``
      must have ``supports_date_range_sync=False`` and the integration must
      not be added to nightly automation.
    """

    def metadata(self) -> IntegrationMetadata: ...

    async def sync_range(
        self,
        *,
        account_id: str,
        start: date,
        end: date,
        recompute: bool = False,
    ) -> IntegrationSyncSummary: ...

    def normalize(self, payload: dict[str, Any]) -> SourceEvent: ...


__all__ = [
    "AuthType",
    "SyncMode",
    "ConnectorCapability",
    "IntegrationMetadata",
    "IntegrationSyncSummary",
    "BaseConnector",
]
