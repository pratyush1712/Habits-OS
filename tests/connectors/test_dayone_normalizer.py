"""Pure-normalizer tests for the Day One connector."""

from __future__ import annotations

from datetime import date, datetime, timezone

from packages.connectors.dayone.normalizer import (
    RAW_PAYLOAD_ALLOWED_KEYS,
    normalize_entries_to_events,
)
from packages.connectors.dayone.sqlite_reader import EntryRow


SNAPSHOT_AT = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)


def _row(
    *,
    uuid: str,
    day: date,
    hour: int = 9,
    journal_name: str = "Personal",
    journal_id: str = "j-uuid-1",
    tags: tuple[str, ...] | None = None,
    word_count: int | None = None,
) -> EntryRow:
    return EntryRow(
        uuid=uuid,
        creation_utc=datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc),
        local_date=day,
        journal_id=journal_id,
        journal_name=journal_name,
        tags=tags,
        word_count=word_count,
    )


def test_no_rows_emits_no_events():
    events = normalize_entries_to_events(
        [], snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42"
    )
    assert events == []


def test_single_entry_day_emits_one_event_with_count_one():
    row = _row(uuid="a", day=date(2026, 5, 1), hour=9, tags=("morning",))
    events = normalize_entries_to_events(
        [row], snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42"
    )
    assert len(events) == 1
    e = events[0]
    assert e.source == "day_one"
    assert e.event_type == "journal"
    assert e.source_event_id == "dayone:2026-05-01"
    assert e.id == "day_one:dayone:2026-05-01"
    assert e.local_date == date(2026, 5, 1)
    assert e.metrics["entry_count"] == 1
    assert e.metrics["journal_names"] == ["Personal"]
    assert e.metrics["journal_ids"] == ["j-uuid-1"]
    assert e.metrics["tags"] == ["morning"]
    assert e.title == "1 journal entry"
    assert e.description == ""  # never leak description text


def test_multi_entry_day_aggregates_counts_and_uses_first_and_last_timestamps():
    day = date(2026, 5, 1)
    rows = [
        _row(uuid="a", day=day, hour=7, journal_name="Personal", journal_id="j1"),
        _row(uuid="b", day=day, hour=22, journal_name="Work", journal_id="j2", tags=("project",)),
    ]
    events = normalize_entries_to_events(
        rows, snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42"
    )
    assert len(events) == 1
    e = events[0]
    assert e.metrics["entry_count"] == 2
    assert e.metrics["journal_names"] == ["Personal", "Work"]
    assert e.metrics["journal_ids"] == ["j1", "j2"]
    assert e.start_time_utc.hour == 7
    assert e.end_time_utc is not None and e.end_time_utc.hour == 22
    assert e.title == "2 journal entries"


def test_tags_unknown_when_no_row_reports_tags():
    # All rows have tags=None ⇒ metrics.tags is omitted entirely (not [])
    rows = [_row(uuid="a", day=date(2026, 5, 1), tags=None)]
    events = normalize_entries_to_events(
        rows, snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42"
    )
    assert "tags" not in events[0].metrics


def test_tags_union_when_any_row_reports_tags():
    day = date(2026, 5, 1)
    rows = [
        _row(uuid="a", day=day, hour=7, tags=("morning", "gratitude")),
        _row(uuid="b", day=day, hour=22, tags=("evening", "gratitude")),
    ]
    events = normalize_entries_to_events(
        rows, snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42"
    )
    assert events[0].metrics["tags"] == ["evening", "gratitude", "morning"]


def test_word_count_absent_when_include_word_count_false():
    row = _row(uuid="a", day=date(2026, 5, 1), word_count=123)
    events = normalize_entries_to_events(
        [row], snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42",
        include_word_count=False,
    )
    assert "total_word_count" not in events[0].metrics


def test_word_count_summed_when_include_word_count_true():
    day = date(2026, 5, 1)
    rows = [
        _row(uuid="a", day=day, word_count=120),
        _row(uuid="b", day=day, hour=22, word_count=80),
    ]
    events = normalize_entries_to_events(
        rows, snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42",
        include_word_count=True,
    )
    assert events[0].metrics["total_word_count"] == 200


def test_raw_payload_allowlist_is_enforced():
    row = _row(uuid="entry-uuid-a", day=date(2026, 5, 1))
    events = normalize_entries_to_events(
        [row], snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42"
    )
    raw = events[0].raw_payload
    assert set(raw.keys()).issubset(RAW_PAYLOAD_ALLOWED_KEYS)
    assert raw["entry_uuids"] == ["entry-uuid-a"]
    assert raw["snapshot_taken_at"] == SNAPSHOT_AT.isoformat()
    assert raw["db_schema_version"] == "42"
    assert raw["source_kind"] == "dayone_sqlite"
    # And — critically — no text fields anywhere.
    assert "text" not in raw
    assert "markdown" not in raw
    assert "content" not in raw


def test_emits_one_event_per_local_date():
    rows = [
        _row(uuid="a", day=date(2026, 5, 1)),
        _row(uuid="b", day=date(2026, 5, 2)),
        _row(uuid="c", day=date(2026, 5, 2), hour=21),
    ]
    events = normalize_entries_to_events(
        rows, snapshot_taken_at=SNAPSHOT_AT, db_schema_version="42"
    )
    assert [e.local_date for e in events] == [date(2026, 5, 1), date(2026, 5, 2)]
    assert events[1].metrics["entry_count"] == 2
