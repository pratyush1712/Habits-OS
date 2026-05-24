"""HabitOS domain models.

The boundary types: anything that crosses module, file, or process boundaries
should be expressed through one of these. Pure-internal scratch state can stay
as plain Python data structures.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


HabitStatus = Literal["checked", "partial", "warning", "missed", "manual"]
HabitKind = Literal["auto", "manual"]
EventSource = Literal[
    "whoop", "muse", "apple_health", "manual", "calendar", "github", "remarkable"
]
EventType = Literal[
    "workout", "sleep", "recovery", "meditation", "deep_work", "journal", "manual"
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Habit(_Strict):
    """A habit the system tracks. `kind` controls whether the rule engine
    attempts to evaluate it from source events (auto) or only honours manual
    overrides (manual)."""

    key: str
    label: str
    short: str
    kind: HabitKind = "auto"


class SourceEvent(_Strict):
    """A normalized event from a connector or manual import.

    `local_date` is precomputed at ingestion time so the rule engine can group
    events without needing timezone math.
    """

    id: str
    source: EventSource
    source_event_id: str
    event_type: EventType
    start_time_utc: datetime
    end_time_utc: datetime | None = None
    local_date: date
    timezone: str = "UTC"
    title: str = ""
    description: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("start_time_utc", "end_time_utc")
    @classmethod
    def _coerce_utc(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @property
    def duration_minutes(self) -> float | None:
        if self.end_time_utc is None:
            return None
        return (self.end_time_utc - self.start_time_utc).total_seconds() / 60.0


class HabitOverride(_Strict):
    """A user-asserted habit entry. Wins over any computed result."""

    date: date
    habit_key: str
    status: HabitStatus
    summary: str = ""
    description: str = ""
    source: EventSource = "manual"


class HabitEntry(_Strict):
    """The resolved state of one habit on one date, ready to render."""

    date: date
    habit_key: str
    status: HabitStatus
    source: EventSource
    summary: str = ""
    description: str = ""
    confidence: float = 1.0
    linked_source_event_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    manually_overridden: bool = False


class MonthHabitState(_Strict):
    """Everything the renderer needs to produce a monthly PDF."""

    month: str
    habits: list[Habit]
    entries: list[HabitEntry]
    generated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("month")
    @classmethod
    def _check_month(cls, v: str) -> str:
        try:
            year_s, month_s = v.split("-")
            date(int(year_s), int(month_s), 1)
        except Exception as e:
            raise ValueError(f"month must be YYYY-MM, got {v!r}") from e
        return v
