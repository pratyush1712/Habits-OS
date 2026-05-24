"""Shared helpers for the repository layer.

The translation between Pydantic models and BSON documents is centralised
here so individual repos stay short. The only quirk to know:

- BSON has no native `date` type. Python `date` fields are stored as ISO
  strings ("2026-05-01"). Range queries (e.g. month-prefix) work because
  ISO date strings sort chronologically.
- `datetime` fields are stored as BSON ISODate (Pydantic emits them unchanged
  in mode='python').
- `bytes` fields are stored as BSON BinData.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, TypeVar

from pydantic import BaseModel


M = TypeVar("M", bound=BaseModel)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def model_to_doc(model: BaseModel, *, drop_id: bool = True) -> dict[str, Any]:
    """Pydantic → BSON-compatible dict. Drops the model's `id` field by default —
    repos set `_id` explicitly with the natural key."""
    doc = model.model_dump(mode="python")
    if drop_id:
        doc.pop("id", None)
    return _coerce_dates(doc)


def doc_to_model(doc: dict[str, Any], model_cls: type[M], *, id_field: str | None = None) -> M:
    """BSON doc → Pydantic model. If `id_field` is given, `_id` is stringified
    and placed onto that field; otherwise `_id` is dropped."""
    raw = dict(doc)
    _id = raw.pop("_id", None)
    if id_field:
        raw[id_field] = str(_id) if _id is not None else None
    return model_cls.model_validate(raw)


def month_range(month: str) -> tuple[str, str]:
    """Convert YYYY-MM to (inclusive_start, exclusive_end) ISO date strings.

    Use with `{"date": {"$gte": start, "$lt": end}}` for index-friendly month
    queries.
    """
    year, mm = (int(x) for x in month.split("-"))
    if mm == 12:
        end_year, end_mm = year + 1, 1
    else:
        end_year, end_mm = year, mm + 1
    return f"{year:04d}-{mm:02d}-01", f"{end_year:04d}-{end_mm:02d}-01"


def _coerce_dates(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _coerce_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_dates(v) for v in obj]
    # date but not datetime — BSON would reject the bare date type.
    if isinstance(obj, date) and not isinstance(obj, datetime):
        return obj.isoformat()
    return obj
