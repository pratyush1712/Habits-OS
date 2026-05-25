"""Pure: Day One entry rows → daily-aggregate SourceEvent records.

One SourceEvent per local date. Per-entry events would multiply rows
without adding value: the only habit question is "did I journal today?"

Metadata-only by construction. The ``raw_payload`` field is built from a
fixed allowlist so accidental leaks of entry text cannot happen here.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from packages.connectors.dayone.sqlite_reader import EntryRow
from packages.core.models import SourceEvent


RAW_PAYLOAD_ALLOWED_KEYS = frozenset(
    {"entry_uuids", "snapshot_taken_at", "db_schema_version", "source_kind"}
)


def normalize_entries_to_events(
    rows: Iterable[EntryRow],
    *,
    snapshot_taken_at: datetime,
    db_schema_version: str | None,
    include_word_count: bool = False,
    fallback_timezone: str = "UTC",
) -> list[SourceEvent]:
    """Group rows by ``local_date`` and emit one journal SourceEvent per day.

    ``include_word_count`` only controls whether per-row ``word_count`` is
    summed into ``metrics.total_word_count``. The raw text is never read here.
    """
    by_date: dict = defaultdict(list)
    for row in rows:
        by_date[row.local_date].append(row)

    events: list[SourceEvent] = []
    for local_date, day_rows in sorted(by_date.items()):
        day_rows.sort(key=lambda r: r.creation_utc)
        first = day_rows[0]
        last = day_rows[-1]
        entry_count = len(day_rows)

        journal_names = sorted({r.journal_name for r in day_rows if r.journal_name})
        journal_ids = sorted({r.journal_id for r in day_rows if r.journal_id})

        # Tags: union across the day's entries, but only if at least one row
        # reported tags (tags=None means "unknown" — see sqlite_reader).
        tag_rows = [r for r in day_rows if r.tags is not None]
        tags: list[str] | None
        if tag_rows:
            collected: set[str] = set()
            for r in tag_rows:
                collected.update(r.tags or ())
            tags = sorted(collected)
        else:
            tags = None

        metrics: dict = {
            "entry_count": entry_count,
            "journal_names": journal_names,
            "journal_ids": journal_ids,
        }
        if tags is not None:
            metrics["tags"] = tags
        if include_word_count:
            total_words = sum((r.word_count or 0) for r in day_rows)
            metrics["total_word_count"] = total_words

        raw_payload = {
            "source_kind": "dayone_sqlite",
            "entry_uuids": [r.uuid for r in day_rows],
            "snapshot_taken_at": snapshot_taken_at.astimezone(timezone.utc).isoformat(),
            "db_schema_version": db_schema_version,
        }
        # Defensive enforcement of the allowlist — if a contributor adds a
        # new key here, the assertion fires loudly in tests.
        assert set(raw_payload.keys()).issubset(RAW_PAYLOAD_ALLOWED_KEYS)

        source_event_id = f"dayone:{local_date.isoformat()}"
        noun = "entry" if entry_count == 1 else "entries"
        events.append(
            SourceEvent(
                id=f"day_one:{source_event_id}",
                source="day_one",
                source_event_id=source_event_id,
                event_type="journal",
                start_time_utc=first.creation_utc,
                end_time_utc=last.creation_utc,
                local_date=local_date,
                timezone=fallback_timezone,
                title=f"{entry_count} journal {noun}",
                description="",
                metrics=metrics,
                raw_payload=raw_payload,
            )
        )

    return events


__all__ = ["normalize_entries_to_events", "RAW_PAYLOAD_ALLOWED_KEYS"]
