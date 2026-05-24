"""Smoke test for the HabitOS monthly renderer.

End-to-end check that the pipeline runs against the committed sample JSON and
produces a non-trivial PDF with the expected anchors.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.renderer.render_month import render
from packages.renderer.state_loader import load_month_state


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_JSON = REPO_ROOT / "data" / "sample_month.json"


def test_legacy_sample_loads_into_month_state() -> None:
    state = load_month_state(SAMPLE_JSON)
    assert state.month == "2026-05"
    assert len(state.entries) > 0
    assert all(e.manually_overridden for e in state.entries)


def test_renders_sample_pdf(tmp_path: Path) -> None:
    pytest.importorskip("playwright")
    out_dir = tmp_path / "generated"
    pdf = render(SAMPLE_JSON, out_dir)

    assert pdf.exists(), f"Expected PDF at {pdf}"
    assert pdf.stat().st_size > 10_000, "PDF looks suspiciously small"

    debug_html = out_dir / "2026-05-habit-dashboard.html"
    assert debug_html.exists()
    text = debug_html.read_text()
    assert 'id="month"' in text
    assert 'id="day-2026-05-01"' in text
    assert 'id="day-2026-05-31"' in text
    assert 'id="week-1"' in text
    assert 'id="week-1-review"' in text
    assert 'id="week-5-review"' in text
    assert 'href="#month"' in text
    assert 'href="#day-2026-05-14"' in text
    assert 'href="#week-1-review"' in text


def test_invalid_status_rejected(tmp_path: Path) -> None:
    bad = {
        "month": "2026-05",
        "habits": [{"key": "workout", "label": "Workout", "short": "W"}],
        "days": [
            {"date": "2026-05-01", "entries": [
                {"habit_key": "workout", "status": "spectacular", "summary": "x"}
            ]}
        ],
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError):
        load_month_state(p)
