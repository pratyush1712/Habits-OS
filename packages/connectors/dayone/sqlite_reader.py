"""Read-only, metadata-only reader for the Day One macOS SQLite database.

The reader copies the live database (plus its ``-wal`` / ``-shm``
companions when present) into a temporary directory before opening, so
the Day One app's own writes cannot race with our reads. The copy is
opened read-only via the SQLite URI scheme.

By default the reader returns only metadata fields. ``ZMARKDOWNTEXT`` is
**never** loaded unless ``include_text=True`` is passed explicitly, and
even then the caller is responsible for deciding whether to persist it.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator


# Core Data uses an epoch of 2001-01-01 UTC; Unix epoch is 1970-01-01 UTC.
CORE_DATA_EPOCH_OFFSET_SECONDS = 978_307_200


class DayOneReadError(Exception):
    """Raised when the Day One database cannot be opened or snapshotted."""


class DayOneSchemaError(Exception):
    """Raised when the database is present but does not match the expected
    Day One schema (missing tables/columns we depend on)."""


@dataclass(frozen=True)
class EntryRow:
    uuid: str
    creation_utc: datetime
    local_date: date
    journal_id: str
    journal_name: str
    tags: tuple[str, ...] | None  # None means "could not resolve" (omit, do not assert empty)
    word_count: int | None  # populated only when include_text=True


@dataclass(frozen=True)
class SnapshotResult:
    schema_version: str | None
    tag_pivot_table: str | None
    rows: list[EntryRow]


REQUIRED_ZENTRY_COLUMNS = {
    "ZUUID",
    "ZCREATIONDATE",
    "ZGREGORIANYEAR",
    "ZGREGORIANMONTH",
    "ZGREGORIANDAY",
    "ZJOURNAL",
}
REQUIRED_ZJOURNAL_COLUMNS = {"Z_PK", "ZNAME", "ZUUIDFORAUXILIARYSYNC"}


def read_entries_in_range(
    db_path: Path,
    *,
    start: date,
    end: date,
    include_text: bool = False,
    journal_filter: tuple[str, ...] = (),
) -> SnapshotResult:
    """Snapshot the Day One DB and return entry rows in [start, end] inclusive.

    Raises:
        DayOneReadError: snapshot copy failed or sqlite cannot open the file.
        DayOneSchemaError: file is a SQLite DB but does not look like Day One.
    """
    if not db_path.exists():
        raise DayOneReadError(f"Day One DB not found at {db_path}")

    with _snapshot(db_path) as snapshot_path:
        try:
            uri = f"file:{snapshot_path}?mode=ro&immutable=1"
            conn = sqlite3.connect(uri, uri=True)
        except sqlite3.Error as exc:
            raise DayOneReadError(f"sqlite open failed: {exc}") from exc

        try:
            conn.row_factory = sqlite3.Row
            _validate_schema(conn)
            schema_version = _read_schema_version(conn)
            pivot_table = _resolve_tag_pivot(conn)
            rows = _select_entries(
                conn,
                start=start,
                end=end,
                include_text=include_text,
                journal_filter=journal_filter,
                pivot_table=pivot_table,
            )
        finally:
            conn.close()

    return SnapshotResult(
        schema_version=schema_version,
        tag_pivot_table=pivot_table,
        rows=rows,
    )


@contextmanager
def _snapshot(db_path: Path) -> Iterator[Path]:
    """Copy DayOne.sqlite plus -wal/-shm to a temp dir; clean up on exit."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="habitos_dayone_"))
    try:
        snapshot = tmp_dir / db_path.name
        try:
            shutil.copy2(db_path, snapshot)
            for suffix in ("-wal", "-shm"):
                companion = db_path.with_name(db_path.name + suffix)
                if companion.exists():
                    shutil.copy2(companion, snapshot.with_name(snapshot.name + suffix))
        except OSError as exc:
            raise DayOneReadError(f"Failed to snapshot Day One DB: {exc}") from exc
        yield snapshot
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _validate_schema(conn: sqlite3.Connection) -> None:
    try:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    except sqlite3.DatabaseError as exc:
        raise DayOneSchemaError(f"Not a readable SQLite database: {exc}") from exc

    if "ZENTRY" not in tables or "ZJOURNAL" not in tables:
        raise DayOneSchemaError(
            "Database does not look like Day One — missing ZENTRY/ZJOURNAL tables."
        )

    entry_cols = {row[1] for row in conn.execute("PRAGMA table_info(ZENTRY)")}
    missing_entry = REQUIRED_ZENTRY_COLUMNS - entry_cols
    if missing_entry:
        raise DayOneSchemaError(
            f"ZENTRY missing required columns: {sorted(missing_entry)}"
        )

    journal_cols = {row[1] for row in conn.execute("PRAGMA table_info(ZJOURNAL)")}
    missing_journal = REQUIRED_ZJOURNAL_COLUMNS - journal_cols
    if missing_journal:
        raise DayOneSchemaError(
            f"ZJOURNAL missing required columns: {sorted(missing_journal)}"
        )


def _read_schema_version(conn: sqlite3.Connection) -> str | None:
    try:
        row = conn.execute("SELECT Z_VERSION FROM Z_METADATA LIMIT 1").fetchone()
    except sqlite3.DatabaseError:
        return None
    if row is None:
        return None
    return str(row[0]) if row[0] is not None else None


def _resolve_tag_pivot(conn: sqlite3.Connection) -> str | None:
    """Day One renames the entry↔tag pivot across schema versions
    (Z_8TAGS, Z_11TAGS, Z_17TAGS, ...). Find the one that joins ZENTRY and
    ZTAG and is not the EXCLUDE variant. Returns None when we can't be
    confident — callers must treat tags as 'unknown', not 'empty'."""
    try:
        candidate_names = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name LIKE 'Z_%TAGS' AND name NOT LIKE '%EXCLUDE%'"
            )
        ]
    except sqlite3.DatabaseError:
        return None

    for name in candidate_names:
        try:
            cols = {row[1] for row in conn.execute(f'PRAGMA table_info("{name}")')}
        except sqlite3.DatabaseError:
            continue
        # The pivot should reference both ZENTRY (via Z_NNENTRIES) and ZTAG
        # (via Z_NNTAGS). The exact prefix numbers change between versions,
        # so we look for any column ending in ENTRIES and any ending in TAGS.
        has_entries_col = any(c.endswith("ENTRIES") for c in cols)
        has_tags_col = any(c.endswith("TAGS") for c in cols)
        if has_entries_col and has_tags_col and len(cols) >= 2:
            return name
    return None


def _select_entries(
    conn: sqlite3.Connection,
    *,
    start: date,
    end: date,
    include_text: bool,
    journal_filter: tuple[str, ...],
    pivot_table: str | None,
) -> list[EntryRow]:
    start_core = _date_to_core_data_seconds(start)
    # End is inclusive at the date level; convert end-of-day to Core Data seconds.
    end_core = _date_to_core_data_seconds(end) + 86_400

    word_count_col = ", LENGTH(ZMARKDOWNTEXT) AS markdown_len" if include_text else ""
    sql = f"""
        SELECT
            e.Z_PK AS pk,
            e.ZUUID AS uuid,
            e.ZCREATIONDATE AS creation_core,
            e.ZGREGORIANYEAR AS gy,
            e.ZGREGORIANMONTH AS gm,
            e.ZGREGORIANDAY AS gd,
            j.ZNAME AS journal_name,
            j.ZUUIDFORAUXILIARYSYNC AS journal_uuid
            {word_count_col}
        FROM ZENTRY e
        JOIN ZJOURNAL j ON j.Z_PK = e.ZJOURNAL
        WHERE e.ZCREATIONDATE >= ? AND e.ZCREATIONDATE < ?
          AND COALESCE(e.ZISDRAFT, 0) = 0
          AND COALESCE(j.ZHIDDEN, 0) = 0
          AND COALESCE(j.ZISTRASHJOURNAL, 0) = 0
        ORDER BY e.ZCREATIONDATE ASC
    """
    cursor = conn.execute(sql, (start_core, end_core))
    raw_rows = cursor.fetchall()

    tags_by_pk = _load_tags(conn, pivot_table, [row["pk"] for row in raw_rows])

    filter_set = {name.lower() for name in journal_filter}
    out: list[EntryRow] = []
    for r in raw_rows:
        journal_name = r["journal_name"] or ""
        if filter_set and journal_name.lower() not in filter_set:
            continue
        creation_utc = datetime.fromtimestamp(
            r["creation_core"] + CORE_DATA_EPOCH_OFFSET_SECONDS,
            tz=timezone.utc,
        )
        gy, gm, gd = r["gy"], r["gm"], r["gd"]
        if gy and gm and gd:
            local_date = date(int(gy), int(gm), int(gd))
        else:
            # Fall back to creation timestamp's UTC date when Gregorian fields
            # are absent. Day One normally writes them; older entries may not.
            local_date = creation_utc.date()
        word_count: int | None = None
        if include_text:
            markdown_len = r["markdown_len"] if "markdown_len" in r.keys() else None
            if markdown_len is not None:
                word_count = _approx_word_count_from_length(int(markdown_len))
        out.append(
            EntryRow(
                uuid=str(r["uuid"]),
                creation_utc=creation_utc,
                local_date=local_date,
                journal_id=str(r["journal_uuid"] or ""),
                journal_name=journal_name,
                tags=tags_by_pk.get(int(r["pk"])),
                word_count=word_count,
            )
        )
    return out


def _load_tags(
    conn: sqlite3.Connection,
    pivot_table: str | None,
    entry_pks: list[int],
) -> dict[int, tuple[str, ...]]:
    if pivot_table is None or not entry_pks:
        return {}
    try:
        cols = [row[1] for row in conn.execute(f'PRAGMA table_info("{pivot_table}")')]
    except sqlite3.DatabaseError:
        return {}
    entries_col = next((c for c in cols if c.endswith("ENTRIES")), None)
    tags_col = next((c for c in cols if c.endswith("TAGS")), None)
    if entries_col is None or tags_col is None:
        return {}

    placeholders = ",".join("?" * len(entry_pks))
    sql = f"""
        SELECT p."{entries_col}" AS entry_pk, t.ZNAME AS tag_name
        FROM "{pivot_table}" p
        JOIN ZTAG t ON t.Z_PK = p."{tags_col}"
        WHERE p."{entries_col}" IN ({placeholders})
    """
    try:
        rows = conn.execute(sql, entry_pks).fetchall()
    except sqlite3.DatabaseError:
        return {}

    out: dict[int, list[str]] = {}
    for row in rows:
        name = row["tag_name"]
        if not name:
            continue
        out.setdefault(int(row["entry_pk"]), []).append(str(name))
    return {pk: tuple(sorted(set(names))) for pk, names in out.items()}


def _date_to_core_data_seconds(d: date) -> float:
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return dt.timestamp() - CORE_DATA_EPOCH_OFFSET_SECONDS


def _approx_word_count_from_length(char_count: int) -> int:
    # Rough heuristic — we never persist the text itself, just a derived
    # count when explicitly opted in. Average English word ~= 5 chars + space.
    if char_count <= 0:
        return 0
    return max(1, round(char_count / 6))


__all__ = [
    "CORE_DATA_EPOCH_OFFSET_SECONDS",
    "DayOneReadError",
    "DayOneSchemaError",
    "EntryRow",
    "SnapshotResult",
    "read_entries_in_range",
]
