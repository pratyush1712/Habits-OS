"""Day One connector configuration loaded from environment variables.

Held here (rather than on the global API ``Settings``) to keep the
connector usable in isolation: tests and ad-hoc scripts can instantiate
``DayOneSettings`` directly without booting the API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DayOneSettings:
    sync_mode: str = "sqlite"  # only "sqlite" is implemented for MVP
    db_path: Path | None = None
    include_text: bool = False
    lookback_days: int = 3
    journal_filter: tuple[str, ...] = field(default_factory=tuple)
    fallback_timezone: str = "UTC"

    @property
    def is_configured(self) -> bool:
        return self.db_path is not None and str(self.db_path).strip() != ""


def load_dayone_settings() -> DayOneSettings:
    db_path_raw = os.getenv("DAYONE_DB_PATH", "").strip()
    db_path = Path(db_path_raw).expanduser() if db_path_raw else None
    journal_filter = tuple(
        name.strip()
        for name in os.getenv("DAYONE_JOURNAL_FILTER", "").split(",")
        if name.strip()
    )
    return DayOneSettings(
        sync_mode=os.getenv("DAYONE_SYNC_MODE", "sqlite").strip().lower() or "sqlite",
        db_path=db_path,
        include_text=_env_bool("DAYONE_INCLUDE_TEXT", default=False),
        lookback_days=_env_int("DAYONE_LOOKBACK_DAYS", default=3, minimum=0),
        journal_filter=journal_filter,
        fallback_timezone=os.getenv("DAYONE_TIMEZONE", "UTC").strip() or "UTC",
    )


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"{name} must be a boolean-like value, got {raw!r}")


def _env_int(name: str, *, default: int, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        value = default
    else:
        value = int(raw)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


__all__ = ["DayOneSettings", "load_dayone_settings"]
