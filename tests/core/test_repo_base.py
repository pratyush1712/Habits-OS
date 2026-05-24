"""Unit tests for repository helper functions — no Mongo needed."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from packages.core.models import HabitOverride, RenderJob, SourceAccount
from packages.core.repositories.base import (
    doc_to_model,
    model_to_doc,
    month_range,
)


def test_model_to_doc_converts_date_to_iso_string():
    o = HabitOverride(date=date(2026, 5, 1), habit_key="workout", status="checked")
    doc = model_to_doc(o)
    assert doc["date"] == "2026-05-01"
    assert isinstance(doc["date"], str)
    assert "id" not in doc


def test_model_to_doc_preserves_datetime_and_bytes():
    a = SourceAccount(
        source="whoop",
        external_user_id="u",
        encrypted_access_token=b"\x01\x02",
        connected_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )
    doc = model_to_doc(a)
    assert isinstance(doc["connected_at"], datetime)
    assert isinstance(doc["encrypted_access_token"], (bytes, bytearray))


def test_doc_to_model_round_trip_with_id_field():
    job = RenderJob(month="2026-05")
    doc = model_to_doc(job)
    doc["_id"] = "deadbeefdeadbeefdeadbeef"
    reloaded = doc_to_model(doc, RenderJob, id_field="id")
    assert reloaded.id == "deadbeefdeadbeefdeadbeef"
    assert reloaded.month == "2026-05"


def test_doc_to_model_drops_id_when_not_requested():
    o = HabitOverride(date=date(2026, 5, 1), habit_key="workout", status="checked")
    doc = model_to_doc(o)
    doc["_id"] = "2026-05-01:workout"
    reloaded = doc_to_model(doc, HabitOverride)
    assert reloaded.date == date(2026, 5, 1)


@pytest.mark.parametrize(
    "month,expected",
    [
        ("2026-05", ("2026-05-01", "2026-06-01")),
        ("2026-12", ("2026-12-01", "2027-01-01")),
        ("2026-01", ("2026-01-01", "2026-02-01")),
    ],
)
def test_month_range(month, expected):
    assert month_range(month) == expected
