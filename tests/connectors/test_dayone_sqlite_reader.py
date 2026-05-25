"""Reader tests against a synthetic, Day One-shaped SQLite fixture.

We don't ship a real Day One database; instead we build the minimum
schema the reader needs and verify behavior end to end. This keeps the
test suite portable (no macOS Mac App Store dependency).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from packages.connectors.dayone.sqlite_reader import (
    CORE_DATA_EPOCH_OFFSET_SECONDS,
    DayOneReadError,
    DayOneSchemaError,
    read_entries_in_range,
)


def _core_data_seconds(dt: datetime) -> float:
    return dt.replace(tzinfo=timezone.utc).timestamp() - CORE_DATA_EPOCH_OFFSET_SECONDS


def _build_fixture(
    db_path: Path,
    *,
    pivot_table: str | None = "Z_8TAGS",
    drop_zentry: bool = False,
    drop_zjournal_column: bool = False,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        if not drop_zentry:
            conn.execute(
                """
                CREATE TABLE ZENTRY (
                    Z_PK INTEGER PRIMARY KEY,
                    ZUUID TEXT,
                    ZCREATIONDATE REAL,
                    ZMODIFIEDDATE REAL,
                    ZGREGORIANYEAR INTEGER,
                    ZGREGORIANMONTH INTEGER,
                    ZGREGORIANDAY INTEGER,
                    ZISDRAFT INTEGER,
                    ZJOURNAL INTEGER,
                    ZMARKDOWNTEXT TEXT,
                    ZRICHTEXTJSON TEXT,
                    ZTIMEZONE BLOB
                )
                """
            )
        journal_cols = "Z_PK INTEGER PRIMARY KEY, ZNAME TEXT, ZHIDDEN INTEGER, ZISTRASHJOURNAL INTEGER"
        if not drop_zjournal_column:
            journal_cols += ", ZUUIDFORAUXILIARYSYNC TEXT"
        conn.execute(f"CREATE TABLE ZJOURNAL ({journal_cols})")
        conn.execute(
            "CREATE TABLE ZTAG (Z_PK INTEGER PRIMARY KEY, ZNAME TEXT, ZNORMALIZEDNAME TEXT)"
        )
        if pivot_table is not None:
            conn.execute(
                f'CREATE TABLE "{pivot_table}" (Z_8ENTRIES INTEGER, Z_18TAGS INTEGER)'
            )
        # Always create the exclude variant so the pivot resolver has to skip it.
        conn.execute('CREATE TABLE "Z_8EXCLUDETAGS" (Z_8ENTRIES INTEGER, Z_18TAGS INTEGER)')
        conn.execute("CREATE TABLE Z_METADATA (Z_VERSION INTEGER, Z_UUID TEXT, Z_PLIST BLOB)")
        conn.execute("INSERT INTO Z_METADATA (Z_VERSION) VALUES (42)")

        if not drop_zjournal_column:
            conn.executemany(
                "INSERT INTO ZJOURNAL (Z_PK, ZNAME, ZHIDDEN, ZISTRASHJOURNAL, ZUUIDFORAUXILIARYSYNC) VALUES (?, ?, ?, ?, ?)",
                [
                    (1, "Personal", 0, 0, "journal-personal-uuid"),
                    (2, "Work", 0, 0, "journal-work-uuid"),
                    (3, "Trash", 0, 1, "journal-trash-uuid"),
                    (4, "Hidden", 1, 0, "journal-hidden-uuid"),
                ],
            )
        if not drop_zentry:
            entries = [
                # Personal, 2026-05-01 morning, non-draft
                (10, "e-1", _core_data_seconds(datetime(2026, 5, 1, 8, 30)), None, 2026, 5, 1, 0, 1, None, None, b""),
                # Personal, 2026-05-01 evening, non-draft
                (11, "e-2", _core_data_seconds(datetime(2026, 5, 1, 21, 0)), None, 2026, 5, 1, 0, 1, "hello world", None, b""),
                # Work, 2026-05-02
                (12, "e-3", _core_data_seconds(datetime(2026, 5, 2, 14, 0)), None, 2026, 5, 2, 0, 2, None, None, b""),
                # Draft (should be filtered out)
                (13, "e-draft", _core_data_seconds(datetime(2026, 5, 1, 9, 0)), None, 2026, 5, 1, 1, 1, None, None, b""),
                # Trash journal (should be filtered out)
                (14, "e-trash", _core_data_seconds(datetime(2026, 5, 1, 10, 0)), None, 2026, 5, 1, 0, 3, None, None, b""),
                # Outside range
                (15, "e-out", _core_data_seconds(datetime(2026, 4, 30, 12, 0)), None, 2026, 4, 30, 0, 1, None, None, b""),
            ]
            conn.executemany(
                "INSERT INTO ZENTRY (Z_PK, ZUUID, ZCREATIONDATE, ZMODIFIEDDATE, ZGREGORIANYEAR, ZGREGORIANMONTH, ZGREGORIANDAY, ZISDRAFT, ZJOURNAL, ZMARKDOWNTEXT, ZRICHTEXTJSON, ZTIMEZONE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                entries,
            )
        conn.executemany(
            "INSERT INTO ZTAG (Z_PK, ZNAME, ZNORMALIZEDNAME) VALUES (?, ?, ?)",
            [(100, "morning", "morning"), (101, "gratitude", "gratitude")],
        )
        if pivot_table is not None:
            # entry 10 tagged "morning"; entry 11 tagged "morning" and "gratitude"
            conn.executemany(
                f'INSERT INTO "{pivot_table}" (Z_8ENTRIES, Z_18TAGS) VALUES (?, ?)',
                [(10, 100), (11, 100), (11, 101)],
            )
        conn.commit()
    finally:
        conn.close()


def test_reader_returns_entries_in_range(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db)
    snapshot = read_entries_in_range(db, start=date(2026, 5, 1), end=date(2026, 5, 2))
    uuids = [r.uuid for r in snapshot.rows]
    # Draft + Trash + out-of-range entries are filtered out.
    assert uuids == ["e-1", "e-2", "e-3"]
    # Schema version surfaces.
    assert snapshot.schema_version == "42"
    # Pivot table is detected, EXCLUDE variant is skipped.
    assert snapshot.tag_pivot_table == "Z_8TAGS"


def test_reader_uses_gregorian_local_date(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db)
    snapshot = read_entries_in_range(db, start=date(2026, 5, 1), end=date(2026, 5, 2))
    by_uuid = {r.uuid: r for r in snapshot.rows}
    assert by_uuid["e-1"].local_date == date(2026, 5, 1)
    assert by_uuid["e-2"].local_date == date(2026, 5, 1)
    assert by_uuid["e-3"].local_date == date(2026, 5, 2)


def test_reader_resolves_tags_for_each_entry(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db)
    snapshot = read_entries_in_range(db, start=date(2026, 5, 1), end=date(2026, 5, 2))
    by_uuid = {r.uuid: r for r in snapshot.rows}
    assert by_uuid["e-1"].tags == ("morning",)
    assert by_uuid["e-2"].tags == ("gratitude", "morning")
    # e-3 was not in the pivot table at all; tags should be None
    # (unknown), not the empty tuple.
    assert by_uuid["e-3"].tags is None


def test_reader_returns_none_pivot_when_no_pivot_table(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db, pivot_table=None)
    snapshot = read_entries_in_range(db, start=date(2026, 5, 1), end=date(2026, 5, 2))
    assert snapshot.tag_pivot_table is None
    for row in snapshot.rows:
        assert row.tags is None


def test_reader_excludes_text_by_default(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db)
    snapshot = read_entries_in_range(db, start=date(2026, 5, 1), end=date(2026, 5, 2))
    for row in snapshot.rows:
        assert row.word_count is None


def test_reader_word_count_when_include_text_true(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db)
    snapshot = read_entries_in_range(
        db, start=date(2026, 5, 1), end=date(2026, 5, 2), include_text=True
    )
    by_uuid = {r.uuid: r for r in snapshot.rows}
    # "hello world" (11 chars) → roughly 2 words via the heuristic
    assert by_uuid["e-2"].word_count is not None and by_uuid["e-2"].word_count >= 1
    # Empty/null markdown ⇒ word_count stays None
    assert by_uuid["e-1"].word_count is None


def test_reader_honors_journal_filter(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db)
    snapshot = read_entries_in_range(
        db,
        start=date(2026, 5, 1),
        end=date(2026, 5, 2),
        journal_filter=("Work",),
    )
    assert [r.uuid for r in snapshot.rows] == ["e-3"]


def test_missing_file_raises_read_error(tmp_path: Path) -> None:
    with pytest.raises(DayOneReadError):
        read_entries_in_range(
            tmp_path / "does_not_exist.sqlite",
            start=date(2026, 5, 1),
            end=date(2026, 5, 2),
        )


def test_missing_zentry_raises_schema_error(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db, drop_zentry=True)
    with pytest.raises(DayOneSchemaError):
        read_entries_in_range(db, start=date(2026, 5, 1), end=date(2026, 5, 2))


def test_missing_required_zjournal_column_raises_schema_error(tmp_path: Path) -> None:
    db = tmp_path / "DayOne.sqlite"
    _build_fixture(db, drop_zjournal_column=True)
    with pytest.raises(DayOneSchemaError):
        read_entries_in_range(db, start=date(2026, 5, 1), end=date(2026, 5, 2))
