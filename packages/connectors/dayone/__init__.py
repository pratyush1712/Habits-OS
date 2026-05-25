"""Day One connector (metadata-only, read-only SQLite reader).

This connector reads the local Day One macOS app database. By default it
captures only metadata (entry counts, journal names, tag names when the
pivot table can be resolved) and never reads or persists entry text. Full
text and word counts are gated behind ``DAYONE_INCLUDE_TEXT=true`` and are
intentionally out of scope for the MVP.
"""

from packages.connectors.dayone.config import DayOneSettings, load_dayone_settings
from packages.connectors.dayone.normalizer import normalize_entries_to_events
from packages.connectors.dayone.sqlite_reader import (
    DayOneReadError,
    DayOneSchemaError,
    EntryRow,
    SnapshotResult,
    read_entries_in_range,
)

__all__ = [
    "DayOneSettings",
    "load_dayone_settings",
    "normalize_entries_to_events",
    "DayOneReadError",
    "DayOneSchemaError",
    "EntryRow",
    "SnapshotResult",
    "read_entries_in_range",
]
