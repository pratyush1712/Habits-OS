"""Declarative index specs for every HabitOS collection.

Unique natural keys are encoded in `_id` (e.g. `f"{source}:{source_event_id}"`
for source_events), so the indexes here are only the secondary ones needed
for query patterns. `ensure_indexes` is idempotent and safe to call at every
application startup.
"""

from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, IndexModel


INDEX_SPECS: dict[str, list[IndexModel]] = {
    "source_events": [
        IndexModel([("local_date", ASCENDING), ("event_type", ASCENDING)], name="local_date_event_type"),
        IndexModel([("start_time_utc", DESCENDING)], name="start_time_recency"),
        IndexModel([("source", ASCENDING), ("local_date", DESCENDING)], name="source_local_date"),
    ],
    "manual_overrides": [
        IndexModel([("date", ASCENDING)], name="by_date"),
    ],
    "habit_entries": [
        IndexModel([("date", ASCENDING), ("status", ASCENDING)], name="date_status"),
        IndexModel([("ruleset_version", ASCENDING)], name="ruleset_version"),
    ],
    "render_jobs": [
        IndexModel([("month", ASCENDING), ("requested_at", DESCENDING)], name="month_recent"),
        IndexModel([("status", ASCENDING), ("requested_at", DESCENDING)], name="status_recent"),
    ],
    "source_accounts": [
        IndexModel([("source", ASCENDING)], name="by_source"),
    ],
    "habits": [
        IndexModel([("archived_at", ASCENDING)], name="by_archived_at"),
    ],
}


async def ensure_indexes(db) -> dict[str, list[str]]:
    """Create every declared index. Returns {collection: [index_name, ...]}.

    Safe to call repeatedly: MongoDB no-ops when the index already exists with
    the same spec.
    """
    created: dict[str, list[str]] = {}
    for coll_name, specs in INDEX_SPECS.items():
        names = await db[coll_name].create_indexes(specs)
        created[coll_name] = names
    return created
