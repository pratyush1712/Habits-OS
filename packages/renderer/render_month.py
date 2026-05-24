"""HabitOS monthly PDF renderer.

Reads a month JSON file (see data/sample_month.json) and writes a hyperlinked
PDF at data/generated/<YYYY-MM>-habit-dashboard.pdf.

Usage:
    python -m packages.renderer.render_month data/sample_month.json
"""

from __future__ import annotations

import argparse
import calendar
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from packages.renderer.links import MONTH_ANCHOR, day_anchor, week_anchor, week_review_anchor

PKG_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PKG_DIR / "templates"
STATIC_DIR = PKG_DIR / "static"

STATUS_GLYPH: dict[str, str] = {
    "checked": "●",
    "partial": "◐",
    "warning": "△",
    "missed": "○",
    "manual": "◆",
}

VALID_STATUSES = set(STATUS_GLYPH) | {"none"}

WEEKDAY_HEADERS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_LONG = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


@dataclass
class CalendarCell:
    """One cell in the monthly grid — either a real day or a filler."""
    iso: str | None
    day: int | None
    weekday_short: str | None
    is_today: bool

    def __bool__(self) -> bool:
        return self.iso is not None


def _build_calendar_rows(year: int, month: int, today: date) -> list[list[CalendarCell]]:
    """Return 7-column rows. cal.Calendar starts the week on Monday."""
    cal = calendar.Calendar(firstweekday=0)
    rows: list[list[CalendarCell]] = []
    for week in cal.monthdatescalendar(year, month):
        row: list[CalendarCell] = []
        for d in week:
            if d.month != month:
                row.append(CalendarCell(iso=None, day=None, weekday_short=None, is_today=False))
            else:
                row.append(
                    CalendarCell(
                        iso=d.isoformat(),
                        day=d.day,
                        weekday_short=WEEKDAY_HEADERS[d.weekday()],
                        is_today=(d == today),
                    )
                )
        rows.append(row)
    return rows


def _build_weeks(rows: list[list[CalendarCell]], days_by_date: dict[str, dict], habits: list[dict]) -> list[dict]:
    weeks: list[dict] = []
    for i, row in enumerate(rows, start=1):
        in_month = [c for c in row if c]
        if not in_month:
            continue
        first = in_month[0]
        last = in_month[-1]
        first_d = date.fromisoformat(first.iso)
        last_d = date.fromisoformat(last.iso)
        # Count days where each habit landed at "checked" or "partial".
        habit_counts: dict[str, int] = {}
        for h in habits:
            count = 0
            for cell in in_month:
                entry = days_by_date[cell.iso]["by_habit"].get(h["key"])
                if entry and entry.get("status") in ("checked", "partial", "manual"):
                    count += 1
            habit_counts[h["key"]] = count
        weeks.append({
            "index": i,
            "anchor": week_anchor(i),
            "review_anchor": week_review_anchor(i),
            "label": f"Week {i}",
            "plan_label": f"Week {i} · Plan",
            "review_label": f"Week {i} · Review",
            "start_label": first_d.strftime("%a %b ") + str(first_d.day),
            "end_label": last_d.strftime("%a %b ") + str(last_d.day),
            "dates": in_month,
            "habit_counts": habit_counts,
        })
    return weeks


def _normalize_days(
    data: dict[str, Any],
    rows: list[list[CalendarCell]],
    weeks: list[dict],
) -> dict[str, dict]:
    """Index input days by ISO date; fill in blanks for any missing day in the month."""
    raw_by_date = {d["date"]: d for d in data.get("days", [])}
    days_by_date: dict[str, dict] = {}
    for row in rows:
        for cell in row:
            if not cell:
                continue
            raw = raw_by_date.get(cell.iso, {})
            entries = raw.get("entries", [])
            for e in entries:
                if e.get("status") not in VALID_STATUSES:
                    raise ValueError(
                        f"Invalid status {e.get('status')!r} on {cell.iso} for habit {e.get('habit_key')!r}"
                    )
            days_by_date[cell.iso] = {
                "date": cell.iso,
                "entries": entries,
                "by_habit": {e["habit_key"]: e for e in entries},
                "notes": raw.get("notes", ""),
            }

    # Wire up week + prev/next + label fields.
    ordered_dates = sorted(days_by_date)
    week_lookup = {cell.iso: w for w in weeks for cell in w["dates"]}
    for i, iso in enumerate(ordered_dates):
        d = date.fromisoformat(iso)
        day = days_by_date[iso]
        day["weekday_long"] = WEEKDAY_LONG[d.weekday()]
        day["month_day_long"] = d.strftime("%B ") + str(d.day)
        day["prev_iso"] = ordered_dates[i - 1] if i > 0 else None
        day["next_iso"] = ordered_dates[i + 1] if i < len(ordered_dates) - 1 else None
        w = week_lookup.get(iso)
        day["week_anchor"] = w["anchor"] if w else None
        day["week_label"] = w["label"] if w else None
    return days_by_date


def _validate_input(data: dict[str, Any]) -> None:
    if "month" not in data:
        raise ValueError("Input JSON must include a 'month' field of the form YYYY-MM.")
    try:
        year, month = (int(x) for x in data["month"].split("-"))
        date(year, month, 1)
    except Exception as e:
        raise ValueError(f"Invalid month {data['month']!r}: {e}") from e
    if not data.get("habits"):
        raise ValueError("Input JSON must include a non-empty 'habits' list.")
    for h in data["habits"]:
        if not h.get("key") or not h.get("label"):
            raise ValueError(f"Habit entries must have 'key' and 'label': {h!r}")


def render(json_path: Path, out_dir: Path, today: date | None = None) -> Path:
    data = json.loads(Path(json_path).read_text())
    _validate_input(data)

    year, month = (int(x) for x in data["month"].split("-"))
    month_label = date(year, month, 1).strftime("%B %Y")
    today = today or date.today()

    rows = _build_calendar_rows(year, month, today)
    # We need days indexed before computing weeks so weekly habit-counts work.
    days_by_date = _normalize_days(data, rows, weeks=[])
    weeks = _build_weeks(rows, days_by_date, data["habits"])
    # Re-attach week info onto each day now that weeks exist.
    week_lookup = {cell.iso: w for w in weeks for cell in w["dates"]}
    for iso, day in days_by_date.items():
        w = week_lookup.get(iso)
        day["week_anchor"] = w["anchor"] if w else None
        day["week_label"] = w["label"] if w else None

    css = (STATIC_DIR / "remarkable.css").read_text()

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("base.html")

    ordered_days = [days_by_date[iso] for iso in sorted(days_by_date)]
    html = template.render(
        css=css,
        month_label=month_label,
        month_str=data["month"],
        habits=data["habits"],
        calendar_rows=rows,
        weeks=weeks,
        days=ordered_days,
        days_by_date=days_by_date,
        weekday_headers=WEEKDAY_HEADERS,
        status_glyph=STATUS_GLYPH,
        month_anchor=MONTH_ANCHOR,
    )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / f"{data['month']}-habit-dashboard.pdf"

    # Save the intermediate HTML alongside the PDF for debugging.
    (out_dir / f"{data['month']}-habit-dashboard.html").write_text(html)

    _html_to_pdf(html, out_pdf)
    return out_pdf


def _html_to_pdf(html: str, out_pdf: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.emulate_media(media="print")
            page.pdf(
                path=str(out_pdf),
                width="157mm",
                height="210mm",
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                print_background=True,
                prefer_css_page_size=True,
            )
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a HabitOS monthly PDF for reMarkable 2.")
    parser.add_argument("json_path", type=Path, help="Path to a month JSON file")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/generated"),
        help="Directory to write the PDF into (default: data/generated)",
    )
    args = parser.parse_args(argv)
    pdf = render(args.json_path, args.out_dir)
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
