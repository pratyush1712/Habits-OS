"""Day One synchronization service.

Boundary between the Day One SQLite reader and HabitOS persistence. The
reader returns metadata rows; the normalizer turns them into one
``SourceEvent`` per local date; this service performs the idempotent
upsert and reports back an ``IntegrationSyncSummary``.

The service never raises in the nightly path: missing DB path, missing
file, unreadable file, or schema mismatch all return a summary with
``skipped_reason`` set.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from packages.connectors.base import (
    AuthType,
    ConnectorCapability,
    IntegrationMetadata,
    IntegrationSyncSummary,
    SyncMode,
)
from packages.connectors.dayone import (
    DayOneReadError,
    DayOneSchemaError,
    DayOneSettings,
    normalize_entries_to_events,
    read_entries_in_range,
)
from packages.core.repositories import SourceEventsRepo

from apps.api.services.habit_evaluation import HabitEvaluationService


SOURCE: str = "day_one"
DOCS_PATH: str = "docs/integrations/dayone.md"
REQUIRED_ENV_VARS: list[str] = ["DAYONE_DB_PATH"]


class DayOneSyncService:
    def __init__(
        self,
        settings: DayOneSettings,
        events_repo: SourceEventsRepo,
        evaluation: HabitEvaluationService,
    ) -> None:
        self.settings = settings
        self.events_repo = events_repo
        self.evaluation = evaluation

    @staticmethod
    def metadata() -> IntegrationMetadata:
        return IntegrationMetadata(
            source=SOURCE,
            display_name="Day One",
            auth_type=AuthType.LOCAL_FILE,
            sync_modes=[SyncMode.IMPORT_FILE],
            capabilities=ConnectorCapability(
                nightly_eligible=True,
                supports_date_range_sync=True,
                supports_backfill=True,
                supports_reconciliation=True,
                recommended_reconcile_window_days=3,
                service_revises_historical_data=True,
                sync_is_idempotent=True,
                required_env_vars=list(REQUIRED_ENV_VARS),
                graceful_when_unconfigured=True,
            ),
            docs_path=DOCS_PATH,
        )

    def is_configured(self) -> bool:
        return self.settings.is_configured

    async def status(self) -> dict:
        db_path = self.settings.db_path
        db_exists = bool(db_path and db_path.exists())
        return {
            "configured": self.is_configured(),
            "sync_mode": self.settings.sync_mode,
            "db_path_configured": self.is_configured(),
            "db_exists": db_exists,
            "include_text": self.settings.include_text,
            "lookback_days": self.settings.lookback_days,
            "journal_filter": list(self.settings.journal_filter),
        }

    async def sync_range(
        self,
        *,
        account_id: str | None = None,
        start: date,
        end: date,
        recompute: bool = False,
    ) -> IntegrationSyncSummary:
        if end < start:
            raise ValueError("end must be on or after start")

        summary = IntegrationSyncSummary(
            source=SOURCE,
            account_id=account_id,
            start=start,
            end=end,
        )

        if self.settings.sync_mode != "sqlite":
            summary.skipped_reason = "unsupported_sync_mode"
            summary.warnings.append(
                f"DAYONE_SYNC_MODE={self.settings.sync_mode!r} not implemented; only 'sqlite' is supported."
            )
            return summary

        if not self.settings.is_configured:
            summary.skipped_reason = "missing_db_path"
            return summary

        db_path = self.settings.db_path
        assert db_path is not None  # narrowed by is_configured
        if not db_path.exists():
            summary.skipped_reason = "dayone_db_unavailable"
            summary.warnings.append(f"Day One DB not found at {db_path}")
            return summary

        # SQLite I/O is blocking; push it off the event loop so we don't
        # stall the FastAPI worker for the duration of the snapshot+read.
        try:
            snapshot = await asyncio.to_thread(
                read_entries_in_range,
                db_path,
                start=start,
                end=end,
                include_text=self.settings.include_text,
                journal_filter=self.settings.journal_filter,
            )
        except DayOneSchemaError as exc:
            summary.skipped_reason = "dayone_schema_unsupported"
            summary.warnings.append(str(exc))
            return summary
        except DayOneReadError as exc:
            summary.skipped_reason = "dayone_db_unreadable"
            summary.warnings.append(str(exc))
            return summary

        snapshot_taken_at = datetime.now(timezone.utc)
        events = normalize_entries_to_events(
            snapshot.rows,
            snapshot_taken_at=snapshot_taken_at,
            db_schema_version=snapshot.schema_version,
            include_word_count=self.settings.include_text,
            fallback_timezone=self.settings.fallback_timezone,
        )

        counts = await self.events_repo.upsert_many_counts(events)
        deleted = await self.events_repo.delete_by_source_date_range_except(
            source=SOURCE,
            event_type="journal",
            start=start,
            end=end,
            keep_ids={event.id for event in events},
        )
        summary.inserted = counts["inserted"]
        summary.updated = counts["updated"]
        summary.event_counts_by_type = {"journal": len(events)} if events else {}
        summary.affected_months = _months_in_range(start, end)
        if deleted:
            summary.extra["deleted"] = deleted

        if recompute:
            for month in summary.affected_months:
                await self.evaluation.recompute(month)

        return summary


def _months_in_range(start: date, end: date) -> list[str]:
    months: list[str] = []
    cursor = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while cursor <= end_month:
        months.append(cursor.strftime("%Y-%m"))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return months


def summary_to_status_dict(summary: IntegrationSyncSummary) -> dict:
    """Render a Day One IntegrationSyncSummary for /automation/status.

    Drops journal names, tags, and entry UUIDs by design — only counts,
    affected months, skipped_reason, errors/warnings cross this boundary.
    """
    return {
        "source": summary.source,
        "start": summary.start.isoformat(),
        "end": summary.end.isoformat(),
        "inserted": summary.inserted,
        "updated": summary.updated,
        "event_counts_by_type": dict(summary.event_counts_by_type),
        "affected_months": list(summary.affected_months),
        "skipped_reason": summary.skipped_reason,
        "errors": list(summary.errors),
        "warnings": list(summary.warnings),
    }


__all__ = ["DayOneSyncService", "summary_to_status_dict", "SOURCE"]
