"""Integration tests for SourceEventsRepo."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from packages.core.models import SourceEvent
from packages.core.repositories import SourceEventsRepo


def _event(day: date, *, source_event_id: str, minutes: int = 30, event_type: str = "workout"):
    start = datetime(day.year, day.month, day.day, 13, 0, tzinfo=timezone.utc)
    return SourceEvent(
        id=f"whoop:{source_event_id}",
        source="whoop",
        source_event_id=source_event_id,
        event_type=event_type,
        start_time_utc=start,
        end_time_utc=start + timedelta(minutes=minutes),
        local_date=day,
        title="test",
    )


async def test_upsert_and_get_round_trip(db):
    repo = SourceEventsRepo(db)
    e = _event(date(2026, 5, 1), source_event_id="a")
    await repo.upsert(e)

    got = await repo.get(e.id)
    assert got is not None
    assert got.id == e.id
    assert got.local_date == date(2026, 5, 1)
    assert got.event_type == "workout"
    assert got.duration_minutes == 30.0


async def test_upsert_many_is_idempotent(db):
    repo = SourceEventsRepo(db)
    events = [_event(date(2026, 5, d), source_event_id=f"e{d}") for d in range(1, 4)]

    n1 = await repo.upsert_many(events)
    n2 = await repo.upsert_many(events)
    assert n1 == 3 and n2 == 3

    all_in_month = await repo.list_by_month("2026-05")
    assert len(all_in_month) == 3


async def test_list_by_local_date(db):
    repo = SourceEventsRepo(db)
    await repo.upsert_many([
        _event(date(2026, 5, 1), source_event_id="a"),
        _event(date(2026, 5, 1), source_event_id="b"),
        _event(date(2026, 5, 2), source_event_id="c"),
    ])

    same_day = await repo.list_by_local_date(date(2026, 5, 1))
    assert {e.id for e in same_day} == {"whoop:a", "whoop:b"}


async def test_list_by_month_filters_adjacent_months(db):
    repo = SourceEventsRepo(db)
    await repo.upsert_many([
        _event(date(2026, 4, 30), source_event_id="apr"),
        _event(date(2026, 5, 1), source_event_id="may"),
        _event(date(2026, 6, 1), source_event_id="jun"),
    ])

    in_may = await repo.list_by_month("2026-05")
    assert [e.source_event_id for e in in_may] == ["may"]


async def test_delete(db):
    repo = SourceEventsRepo(db)
    e = _event(date(2026, 5, 1), source_event_id="x")
    await repo.upsert(e)
    assert await repo.delete(e.id) is True
    assert await repo.get(e.id) is None
    assert await repo.delete(e.id) is False
