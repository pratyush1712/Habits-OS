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
    "whoop",
    "muse",
    "apple_health",
    "manual",
    "calendar",
    "github",
    "remarkable",
    "day_one",
    "medication",
]
EventType = Literal[
    "workout",
    "sleep",
    "recovery",
    "meditation",
    "deep_work",
    "journal",
    "manual",
    "medication",
    "protein_shake",
]
MedicationDoseStatus = Literal["taken", "partial", "missed", "none"]



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Habit(_Strict):
    """A habit the system tracks. `kind` controls whether the rule engine
    attempts to evaluate it from source events (auto) or only honours manual
    overrides (manual).

    `metric_only` habits are still computed and stored (so their data stays
    available), but they are not user-controlled checkboxes. The renderer shows
    them as context metrics (e.g. sleep duration, recovery score next to the
    date) rather than as habit cards in the grid or tally. Use this for signals
    that reflect the body's state rather than a deliberate action."""

    key: str
    label: str
    short: str
    kind: HabitKind = "auto"
    enabled: bool = True
    metric_only: bool = False
    sort_order: int = 100
    description: str = ""
    event_types: list[EventType] = Field(default_factory=list)
    sources: list[EventSource] = Field(default_factory=list)




class MedicationItem(_Strict):
    """A medication or supplement in the renderer schedule.

    This is schedule/display metadata, not medical advice. Historical dose logs
    stay in ``SourceEvent`` records so the regimen can change without rewriting
    old adherence data.
    """

    key: str
    label: str
    short: str
    dose: str = ""
    total: int = Field(default=1, ge=0)
    prn: bool = False


class MedicationGroup(_Strict):
    """A time-of-day bucket for the medication schedule shown in the PDF."""

    key: str
    label: str
    meds: list[MedicationItem] = Field(default_factory=list)


class MedicationDayDose(_Strict):
    """One day's observed dose count for one medication/supplement."""

    date: date
    med_key: str
    taken: int = Field(default=0, ge=0)
    total: int | None = Field(default=None, ge=0)
    status: MedicationDoseStatus | None = None

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
    medication_groups: list[MedicationGroup] = Field(default_factory=list)
    medication_days: list[MedicationDayDose] = Field(default_factory=list)
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


RenderJobStatus = Literal["pending", "running", "completed", "failed"]
RenderTrigger = Literal["manual", "schedule", "webhook"]
AccountStatus = Literal["active", "revoked", "expired"]
AutomationRunType = Literal["nightly", "manual", "rollover"]
AutomationRunStatus = Literal["running", "completed", "failed"]


class RenderJob(_Strict):
    """Audit-trail entry for one PDF render. The repo assigns `id` after insert."""

    id: str | None = None
    month: str
    status: RenderJobStatus = "pending"
    requested_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_path: str | None = None
    ruleset_version: str = "v1"
    triggered_by: RenderTrigger = "manual"
    error: str | None = None


class SourceAccount(_Strict):
    """An OAuth-connected source (WHOOP, Muse, ...).

    Tokens are stored as opaque `bytes` so a future encryption layer can wrap
    them without schema changes. Encryption itself is deferred — see
    CLAUDE.md §10 and docs/persistence.md.
    """

    id: str | None = None
    source: EventSource
    external_user_id: str
    display_name: str = ""
    scopes: list[str] = Field(default_factory=list)
    encrypted_access_token: bytes | None = None
    encrypted_refresh_token: bytes | None = None
    token_expires_at: datetime | None = None
    connected_at: datetime = Field(default_factory=_utcnow)
    last_sync_at: datetime | None = None
    last_webhook_at: datetime | None = None
    status: AccountStatus = "active"


class AutomationRun(_Strict):
    """Audit trail entry for one nightly/manual automation execution."""

    id: str | None = None
    run_type: AutomationRunType
    status: AutomationRunStatus
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None
    dry_run: bool = True
    timezone: str
    date: str
    window: dict[str, Any]
    months: dict[str, Any]
    whoop_summary: dict[str, Any] = Field(default_factory=dict)
    dayone_summary: dict[str, Any] = Field(default_factory=dict)
    habit_recompute_summary: list[dict[str, Any]] = Field(default_factory=list)
    render_summary: dict[str, Any] = Field(default_factory=dict)
    remarkable_summary: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    @field_validator("date")
    @classmethod
    def _check_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"date must be YYYY-MM-DD, got {v!r}") from e
        return v

    @field_validator("window")
    @classmethod
    def _check_window(cls, v: dict[str, Any]) -> dict[str, Any]:
        start = v.get("start")
        end = v.get("end")
        reconcile_days = v.get("reconcile_days")
        if not isinstance(start, str) or not isinstance(end, str):
            raise ValueError("window.start and window.end must be ISO date strings")
        try:
            date.fromisoformat(start)
            date.fromisoformat(end)
        except ValueError as e:
            raise ValueError("window.start and window.end must be YYYY-MM-DD") from e
        if not isinstance(reconcile_days, int) or reconcile_days < 0:
            raise ValueError("window.reconcile_days must be a non-negative integer")
        return v

    @field_validator("months")
    @classmethod
    def _check_months(cls, v: dict[str, Any]) -> dict[str, Any]:
        current = v.get("current")
        previous = v.get("previous")
        affected = v.get("affected")
        if not isinstance(current, str):
            raise ValueError("months.current must be a YYYY-MM string")
        _parse_month_value(current)
        if previous is not None:
            if not isinstance(previous, str):
                raise ValueError("months.previous must be null or a YYYY-MM string")
            _parse_month_value(previous)
        if not isinstance(affected, list) or not all(isinstance(month, str) for month in affected):
            raise ValueError("months.affected must be a list of YYYY-MM strings")
        for month in affected:
            _parse_month_value(month)
        return v


def _parse_month_value(month: str) -> None:
    try:
        year_s, month_s = month.split("-")
        date(int(year_s), int(month_s), 1)
    except Exception as e:
        raise ValueError(f"month must be YYYY-MM, got {month!r}") from e
