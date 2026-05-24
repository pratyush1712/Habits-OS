from __future__ import annotations

from datetime import date

from packages.connectors.whoop.normalizer import (
    normalize_recovery,
    normalize_sleep,
    normalize_workout,
)


WORKOUT = {
    "id": "ecfc6a15-4661-442f-a9a4-f160dd7afae8",
    "v1_id": 1043,
    "user_id": 9012,
    "start": "2026-05-01T13:00:00.000Z",
    "end": "2026-05-01T13:45:00.000Z",
    "timezone_offset": "-04:00",
    "sport_name": "running",
    "sport_id": 1,
    "score_state": "SCORED",
    "score": {
        "strain": 8.2463,
        "average_heart_rate": 123,
        "max_heart_rate": 146,
        "kilojoule": 1569.34,
        "percent_recorded": 100,
        "distance_meter": 5000,
        "zone_durations": {"zone_two_milli": 900000},
    },
}


SLEEP = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "cycle_id": 93845,
    "v1_id": 93845,
    "user_id": 10129,
    "start": "2026-05-02T03:30:00.000Z",
    "end": "2026-05-02T11:00:00.000Z",
    "timezone_offset": "-04:00",
    "nap": False,
    "score_state": "SCORED",
    "score": {
        "stage_summary": {
            "total_in_bed_time_milli": 27000000,
            "total_awake_time_milli": 1200000,
            "total_light_sleep_time_milli": 12000000,
            "total_slow_wave_sleep_time_milli": 5000000,
            "total_rem_sleep_time_milli": 6000000,
        },
        "sleep_needed": {"baseline_milli": 25200000},
        "respiratory_rate": 16.1,
        "sleep_performance_percentage": 98,
        "sleep_consistency_percentage": 90,
        "sleep_efficiency_percentage": 91.7,
    },
}


RECOVERY = {
    "cycle_id": 93845,
    "sleep_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 10129,
    "created_at": "2026-05-02T12:00:00.000Z",
    "updated_at": "2026-05-02T12:05:00.000Z",
    "score_state": "SCORED",
    "score": {
        "user_calibrating": False,
        "recovery_score": 77,
        "resting_heart_rate": 54,
        "hrv_rmssd_milli": 70.5,
        "spo2_percentage": 98.1,
        "skin_temp_celsius": 33.7,
    },
}


def test_normalize_workout_preserves_metrics_and_raw_payload():
    event = normalize_workout(WORKOUT)

    assert event.id == f"whoop:{WORKOUT['id']}"
    assert event.source == "whoop"
    assert event.source_event_id == WORKOUT["id"]
    assert event.event_type == "workout"
    assert event.local_date == date(2026, 5, 1)
    assert event.timezone == "-04:00"
    assert event.title == "running"
    assert event.metrics["strain"] == 8.2463
    assert event.metrics["distance_meter"] == 5000
    assert event.raw_payload == WORKOUT


def test_normalize_sleep_uses_efficiency_metric_key_expected_by_rules():
    event = normalize_sleep(SLEEP)

    assert event.id == f"whoop:{SLEEP['id']}"
    assert event.event_type == "sleep"
    # 03:30Z with -04:00 offset belongs to the prior local date.
    assert event.local_date == date(2026, 5, 1)
    assert event.title == "Main sleep"
    assert event.metrics["efficiency_pct"] == 91.7
    assert event.metrics["total_in_bed_minutes"] == 450
    assert event.raw_payload == SLEEP


def test_normalize_sleep_nap_title():
    payload = {**SLEEP, "id": "nap-id", "nap": True}
    event = normalize_sleep(payload)

    assert event.title == "Nap"
    assert event.metrics["nap"] is True


def test_normalize_recovery_uses_sleep_anchor_when_available():
    event = normalize_recovery(RECOVERY, sleep_payload=SLEEP)

    assert event.id == f"whoop:recovery:{RECOVERY['sleep_id']}"
    assert event.source_event_id == f"recovery:{RECOVERY['sleep_id']}"
    assert event.event_type == "recovery"
    assert event.local_date == date(2026, 5, 1)
    assert event.metrics["recovery_score"] == 77
    assert event.metrics["date_anchor"] == "sleep.start"
    assert event.raw_payload == RECOVERY


def test_normalize_recovery_falls_back_to_created_at():
    event = normalize_recovery({**RECOVERY, "sleep_id": None})

    assert event.source_event_id == "recovery:cycle:93845"
    assert event.local_date == date(2026, 5, 2)
    assert event.metrics["date_anchor"] == "recovery.created_at"
