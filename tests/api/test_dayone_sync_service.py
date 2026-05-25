"""Service-level tests for DayOneSyncService.

We exercise every ``skipped_reason`` path (missing path, missing file,
unreadable DB, schema mismatch, unsupported mode), the happy path with a
fixture DB, and the idempotency invariant (a second run inserts zero
new events).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from apps.api.services.dayone_sync import DayOneSyncService
from packages.connectors.dayone.config import DayOneSettings


def _core_data_seconds(dt: datetime) -> float:
    return dt.replace(tzinfo=timezone.utc).timestamp() - 978_307_200


def _build_minimal_dayone_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE ZENTRY (
                Z_PK INTEGER PRIMARY KEY,
                ZUUID TEXT,
                ZCREATIONDATE REAL,
                ZGREGORIANYEAR INTEGER,
                ZGREGORIANMONTH INTEGER,
                ZGREGORIANDAY INTEGER,
                ZISDRAFT INTEGER,
                ZJOURNAL INTEGER,
                ZMARKDOWNTEXT TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE ZJOURNAL (
                Z_PK INTEGER PRIMARY KEY,
                ZNAME TEXT,
                ZHIDDEN INTEGER,
                ZISTRASHJOURNAL INTEGER,
                ZUUIDFORAUXILIARYSYNC TEXT
            )
            """
        )
        conn.execute("CREATE TABLE Z_METADATA (Z_VERSION INTEGER)")
        conn.execute("INSERT INTO Z_METADATA (Z_VERSION) VALUES (42)")
        conn.execute(
            "INSERT INTO ZJOURNAL (Z_PK, ZNAME, ZHIDDEN, ZISTRASHJOURNAL, ZUUIDFORAUXILIARYSYNC) VALUES (1, 'Personal', 0, 0, 'j-uuid')"
        )
        conn.executemany(
            "INSERT INTO ZENTRY (Z_PK, ZUUID, ZCREATIONDATE, ZGREGORIANYEAR, ZGREGORIANMONTH, ZGREGORIANDAY, ZISDRAFT, ZJOURNAL, ZMARKDOWNTEXT) VALUES (?, ?, ?, ?, ?, ?, 0, 1, NULL)",
            [
                (1, "e-1", _core_data_seconds(datetime(2026, 5, 1, 8, 0)), 2026, 5, 1),
                (2, "e-2", _core_data_seconds(datetime(2026, 5, 1, 22, 0)), 2026, 5, 1),
                (3, "e-3", _core_data_seconds(datetime(2026, 5, 2, 14, 0)), 2026, 5, 2),
            ],
        )
        conn.commit()
    finally:
        conn.close()


class _StubEventsRepo:
    def __init__(self) -> None:
        self.upserted_ids: dict[str, dict] = {}
        self.inserted_count = 0
        self.updated_count = 0

    async def upsert_many_counts(self, events) -> dict:
        inserted = 0
        updated = 0
        for e in events:
            if e.id in self.upserted_ids:
                updated += 1
            else:
                inserted += 1
            self.upserted_ids[e.id] = {
                "source": e.source,
                "source_event_id": e.source_event_id,
                "local_date": e.local_date.isoformat(),
                "metrics": dict(e.metrics),
                "raw_payload_keys": sorted(e.raw_payload.keys()),
            }
        self.inserted_count += inserted
        self.updated_count += updated
        return {"inserted": inserted, "updated": updated, "total": inserted + updated}


class _StubEvaluation:
    def __init__(self) -> None:
        self.recomputed: list[str] = []

    async def recompute(self, month: str) -> dict:
        self.recomputed.append(month)
        return {"month": month, "entries_written": 0, "entries_deleted": 0}


# ---------- skipped reasons ----------


@pytest.mark.asyncio
async def test_missing_db_path_returns_skipped_summary() -> None:
    service = DayOneSyncService(
        DayOneSettings(db_path=None),
        _StubEventsRepo(),
        _StubEvaluation(),
    )
    summary = await service.sync_range(start=date(2026, 5, 1), end=date(2026, 5, 2))
    assert summary.skipped_reason == "missing_db_path"
    assert summary.inserted == 0
    assert summary.affected_months == []


@pytest.mark.asyncio
async def test_unsupported_sync_mode_returns_skipped_summary(tmp_path: Path) -> None:
    service = DayOneSyncService(
        DayOneSettings(sync_mode="mcp", db_path=tmp_path / "x.sqlite"),
        _StubEventsRepo(),
        _StubEvaluation(),
    )
    summary = await service.sync_range(start=date(2026, 5, 1), end=date(2026, 5, 2))
    assert summary.skipped_reason == "unsupported_sync_mode"


@pytest.mark.asyncio
async def test_db_file_missing_returns_skipped_summary(tmp_path: Path) -> None:
    service = DayOneSyncService(
        DayOneSettings(db_path=tmp_path / "missing.sqlite"),
        _StubEventsRepo(),
        _StubEvaluation(),
    )
    summary = await service.sync_range(start=date(2026, 5, 1), end=date(2026, 5, 2))
    assert summary.skipped_reason == "dayone_db_unavailable"


@pytest.mark.asyncio
async def test_db_schema_mismatch_returns_skipped_summary(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    conn = sqlite3.connect(db)
    try:
        # A real SQLite database but not Day One — missing ZENTRY/ZJOURNAL.
        conn.execute("CREATE TABLE NOT_DAYONE (id INTEGER)")
        conn.commit()
    finally:
        conn.close()
    service = DayOneSyncService(
        DayOneSettings(db_path=db),
        _StubEventsRepo(),
        _StubEvaluation(),
    )
    summary = await service.sync_range(start=date(2026, 5, 1), end=date(2026, 5, 2))
    assert summary.skipped_reason == "dayone_schema_unsupported"


@pytest.mark.asyncio
async def test_inverted_range_raises_value_error(tmp_path: Path) -> None:
    service = DayOneSyncService(
        DayOneSettings(db_path=tmp_path / "x.sqlite"),
        _StubEventsRepo(),
        _StubEvaluation(),
    )
    with pytest.raises(ValueError):
        await service.sync_range(start=date(2026, 5, 2), end=date(2026, 5, 1))


# ---------- happy path ----------


@pytest.mark.asyncio
async def test_happy_path_writes_one_event_per_local_date(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_minimal_dayone_db(db)
    events_repo = _StubEventsRepo()
    evaluation = _StubEvaluation()
    service = DayOneSyncService(
        DayOneSettings(db_path=db),
        events_repo,
        evaluation,
    )
    summary = await service.sync_range(
        start=date(2026, 5, 1), end=date(2026, 5, 2), recompute=True
    )
    assert summary.skipped_reason is None
    # Two local dates ⇒ two SourceEvents.
    assert summary.inserted == 2
    assert summary.updated == 0
    assert summary.event_counts_by_type == {"journal": 2}
    assert summary.affected_months == ["2026-05"]
    assert evaluation.recomputed == ["2026-05"]
    # Day 2026-05-01 had two entries.
    by_local_date = {
        v["local_date"]: v for v in events_repo.upserted_ids.values()
    }
    assert by_local_date["2026-05-01"]["metrics"]["entry_count"] == 2
    assert by_local_date["2026-05-02"]["metrics"]["entry_count"] == 1
    # raw_payload allowlist: no leaked text keys.
    for ev in events_repo.upserted_ids.values():
        assert set(ev["raw_payload_keys"]).issubset(
            {"entry_uuids", "snapshot_taken_at", "db_schema_version", "source_kind"}
        )


# ---------- idempotency ----------


@pytest.mark.asyncio
async def test_second_run_inserts_zero_events(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_minimal_dayone_db(db)
    events_repo = _StubEventsRepo()
    service = DayOneSyncService(
        DayOneSettings(db_path=db),
        events_repo,
        _StubEvaluation(),
    )
    first = await service.sync_range(start=date(2026, 5, 1), end=date(2026, 5, 2))
    second = await service.sync_range(start=date(2026, 5, 1), end=date(2026, 5, 2))
    assert first.inserted == 2 and first.updated == 0
    assert second.inserted == 0
    # Day One's running totals: a second sync sees both daily aggregates
    # as updates. The important invariant is no new rows are created.
    assert second.updated == 2


# ---------- metadata + status ----------


@pytest.mark.asyncio
async def test_status_reports_configuration_correctly(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_minimal_dayone_db(db)
    service = DayOneSyncService(
        DayOneSettings(db_path=db, lookback_days=5, journal_filter=("Personal",)),
        _StubEventsRepo(),
        _StubEvaluation(),
    )
    status = await service.status()
    assert status["configured"] is True
    assert status["db_exists"] is True
    assert status["include_text"] is False
    assert status["lookback_days"] == 5
    assert status["journal_filter"] == ["Personal"]


def test_metadata_capabilities_satisfy_contract() -> None:
    meta = DayOneSyncService.metadata()
    assert meta.source == "day_one"
    cap = meta.capabilities
    assert cap.nightly_eligible is True
    assert cap.graceful_when_unconfigured is True
    assert cap.sync_is_idempotent is True
    assert cap.required_env_vars == ["DAYONE_DB_PATH"]
