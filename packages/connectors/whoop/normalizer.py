"""Normalize WHOOP API payloads into HabitOS SourceEvent models.

These functions are intentionally pure: no HTTP, no MongoDB, no settings. They
can be called from manual sync, webhook processing, or tests with the same
result. Full WHOOP payloads are preserved in ``raw_payload`` for audit/debugging
while stable, rule-relevant fields are copied into ``metrics``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from packages.core.models import SourceEvent


JsonObject = dict[str, Any]


def normalize_workout(payload: JsonObject) -> SourceEvent:
    source_event_id = _required_str(payload, "id")
    start = _parse_datetime(_required_str(payload, "start"))
    end = _parse_optional_datetime(payload.get("end"))
    score = _dict(payload.get("score"))
    sport_name = _optional_str(payload.get("sport_name"))

    metrics = _drop_none(
        {
            "strain": score.get("strain"),
            "average_heart_rate": score.get("average_heart_rate"),
            "max_heart_rate": score.get("max_heart_rate"),
            "kilojoule": score.get("kilojoule"),
            "percent_recorded": score.get("percent_recorded"),
            "distance_meter": score.get("distance_meter"),
            "altitude_gain_meter": score.get("altitude_gain_meter"),
            "altitude_change_meter": score.get("altitude_change_meter"),
            "zone_durations": score.get("zone_durations"),
            "sport_id": payload.get("sport_id"),
            "sport_name": sport_name,
            "score_state": payload.get("score_state"),
            "v1_id": payload.get("v1_id"),
            "user_id": payload.get("user_id"),
        }
    )

    return SourceEvent(
        id=_event_id(source_event_id),
        source="whoop",
        source_event_id=source_event_id,
        event_type="workout",
        start_time_utc=start,
        end_time_utc=end,
        local_date=_local_date(start, payload.get("timezone_offset")),
        timezone=_timezone_label(payload.get("timezone_offset")),
        title=sport_name or "WHOOP workout",
        description=_workout_description(metrics),
        metrics=metrics,
        raw_payload=payload,
    )


def normalize_sleep(payload: JsonObject) -> SourceEvent:
    source_event_id = _required_str(payload, "id")
    start = _parse_datetime(_required_str(payload, "start"))
    end = _parse_optional_datetime(payload.get("end"))
    score = _dict(payload.get("score"))
    stage_summary = _dict(score.get("stage_summary"))
    sleep_needed = _dict(score.get("sleep_needed"))
    nap = bool(payload.get("nap", False))

    metrics = _drop_none(
        {
            "nap": nap,
            "cycle_id": payload.get("cycle_id"),
            "v1_id": payload.get("v1_id"),
            "user_id": payload.get("user_id"),
            "score_state": payload.get("score_state"),
            "stage_summary": stage_summary,
            "sleep_needed": sleep_needed,
            "respiratory_rate": score.get("respiratory_rate"),
            "sleep_performance_pct": score.get("sleep_performance_percentage"),
            "sleep_consistency_pct": score.get("sleep_consistency_percentage"),
            # Current sleep summaries look for this generic metric key.
            "efficiency_pct": score.get("sleep_efficiency_percentage"),
            "sleep_efficiency_pct": score.get("sleep_efficiency_percentage"),
            "total_in_bed_minutes": _millis_to_minutes(stage_summary.get("total_in_bed_time_milli")),
            "total_awake_minutes": _millis_to_minutes(stage_summary.get("total_awake_time_milli")),
            "total_light_sleep_minutes": _millis_to_minutes(stage_summary.get("total_light_sleep_time_milli")),
            "total_slow_wave_sleep_minutes": _millis_to_minutes(stage_summary.get("total_slow_wave_sleep_time_milli")),
            "total_rem_sleep_minutes": _millis_to_minutes(stage_summary.get("total_rem_sleep_time_milli")),
        }
    )

    return SourceEvent(
        id=_event_id(source_event_id),
        source="whoop",
        source_event_id=source_event_id,
        event_type="sleep",
        start_time_utc=start,
        end_time_utc=end,
        local_date=_local_date(start, payload.get("timezone_offset")),
        timezone=_timezone_label(payload.get("timezone_offset")),
        title="Nap" if nap else "Main sleep",
        description=_sleep_description(metrics),
        metrics=metrics,
        raw_payload=payload,
    )


def normalize_recovery(payload: JsonObject, sleep_payload: JsonObject | None = None) -> SourceEvent:
    """Normalize a recovery payload.

    WHOOP recovery collection records do not include start/end timestamps. When
    the associated sleep payload is available, use the sleep start as the
    habit-local date anchor. Otherwise fall back to recovery ``created_at``.
    """

    cycle_id = payload.get("cycle_id")
    sleep_id = payload.get("sleep_id")
    if sleep_id:
        source_event_id = f"recovery:{sleep_id}"
    elif cycle_id is not None:
        source_event_id = f"recovery:cycle:{cycle_id}"
    else:
        source_event_id = f"recovery:{_required_str(payload, 'created_at')}"

    anchor_payload = sleep_payload if sleep_payload is not None else payload
    anchor_raw = anchor_payload.get("start") or payload.get("created_at") or payload.get("updated_at")
    anchor = _parse_datetime(_required_text(anchor_raw, "start or created_at"))
    score = _dict(payload.get("score"))

    metrics = _drop_none(
        {
            "cycle_id": cycle_id,
            "sleep_id": sleep_id,
            "user_id": payload.get("user_id"),
            "score_state": payload.get("score_state"),
            "user_calibrating": score.get("user_calibrating"),
            "recovery_score": score.get("recovery_score"),
            "resting_heart_rate": score.get("resting_heart_rate"),
            "hrv_rmssd_milli": score.get("hrv_rmssd_milli"),
            "spo2_percentage": score.get("spo2_percentage"),
            "skin_temp_celsius": score.get("skin_temp_celsius"),
            "date_anchor": "sleep.start" if sleep_payload is not None else "recovery.created_at",
        }
    )

    return SourceEvent(
        id=_event_id(source_event_id),
        source="whoop",
        source_event_id=source_event_id,
        event_type="recovery",
        start_time_utc=anchor,
        end_time_utc=None,
        local_date=_local_date(anchor, anchor_payload.get("timezone_offset")),
        timezone=_timezone_label(anchor_payload.get("timezone_offset")),
        title="Recovery",
        description=_recovery_description(metrics),
        metrics=metrics,
        raw_payload=payload,
    )


def _event_id(source_event_id: str) -> str:
    return f"whoop:{source_event_id}"


def _required_str(payload: JsonObject, key: str) -> str:
    return _required_text(payload.get(key), key)


def _required_text(value: Any, label: str) -> str:
    if value is None or value == "":
        raise ValueError(f"WHOOP payload missing required field: {label}")
    return str(value)


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_optional_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    return _parse_datetime(str(value))


def _local_date(start_utc: datetime, offset_value: Any) -> date:
    offset = _parse_offset(offset_value)
    return (start_utc + offset).date()


def _parse_offset(value: Any) -> timedelta:
    if not value:
        return timedelta(0)
    text = str(value)
    if text == "Z":
        return timedelta(0)
    sign = -1 if text.startswith("-") else 1
    parts = text.lstrip("+-").split(":")
    if len(parts) < 2:
        return timedelta(0)
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        return timedelta(0)
    return sign * timedelta(hours=hours, minutes=minutes)


def _timezone_label(value: Any) -> str:
    return str(value) if value else "UTC"


def _dict(value: Any) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _millis_to_minutes(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value) / 60000.0
    except (TypeError, ValueError):
        return None


def _drop_none(values: JsonObject) -> JsonObject:
    return {k: v for k, v in values.items() if v is not None}


def _workout_description(metrics: JsonObject) -> str:
    parts: list[str] = []
    strain = metrics.get("strain")
    avg_hr = metrics.get("average_heart_rate")
    distance = metrics.get("distance_meter")
    if strain is not None:
        parts.append(f"strain {float(strain):.1f}")
    if avg_hr is not None:
        parts.append(f"avg HR {avg_hr}")
    if distance is not None:
        parts.append(f"{float(distance) / 1000:.1f} km")
    return " · ".join(parts)


def _sleep_description(metrics: JsonObject) -> str:
    parts: list[str] = []
    performance = metrics.get("sleep_performance_pct")
    efficiency = metrics.get("efficiency_pct")
    if performance is not None:
        parts.append(f"performance {performance}%")
    if efficiency is not None:
        parts.append(f"efficiency {float(efficiency):.0f}%")
    return " · ".join(parts)


def _recovery_description(metrics: JsonObject) -> str:
    score = metrics.get("recovery_score")
    rhr = metrics.get("resting_heart_rate")
    hrv = metrics.get("hrv_rmssd_milli")
    parts: list[str] = []
    if score is not None:
        parts.append(f"recovery {score}%")
    if rhr is not None:
        parts.append(f"RHR {rhr}")
    if hrv is not None:
        parts.append(f"HRV {float(hrv):.1f}")
    return " · ".join(parts)
