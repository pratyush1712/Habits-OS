"""HabitOS monthly PDF renderer.

Consumes a `MonthHabitState` (or a JSON file that loads into one) and writes a
hyperlinked PDF at `data/generated/<YYYY-MM>-habit-dashboard.pdf`.

Usage:
    python -m packages.renderer.render_month data/sample_month.json
"""

from __future__ import annotations

import argparse
import calendar
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from packages.core.models import HabitEntry, MedicationDayDose, MedicationItem, MonthHabitState
from packages.renderer.links import (
    MONTH_ANCHOR,
    TALLY_ANCHOR,
    MED_TALLY_ANCHOR,
    week_anchor,
    week_review_anchor,
)
from packages.renderer.state_loader import load_month_state

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


MED_STATUS_GLYPH: dict[str, str] = {
    "taken": "●",
    "partial": "◐",
    "missed": "○",
    "none": "·",
}

WEEKDAY_HEADERS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_LONG = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

_LONG_DECIMAL_RE = re.compile(r"(?P<int>\d+)\.(?P<frac>\d{3,})")


@dataclass
class CalendarCell:
    iso: str | None
    day: int | None
    weekday_short: str | None
    is_today: bool

    def __bool__(self) -> bool:
        return self.iso is not None


def _build_calendar_rows(year: int, month: int, today: date) -> list[list[CalendarCell]]:
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


def _build_days(
    rows: list[list[CalendarCell]],
    entries: list[HabitEntry],
    metric_habits,
    medication_days: list[MedicationDayDose],
) -> dict[str, dict]:
    """Index entries by ISO date and stash per-habit lookup."""
    entries_by_date: dict[str, list[HabitEntry]] = {}
    for e in entries:
        entries_by_date.setdefault(e.date.isoformat(), []).append(_for_render(e))

    medication_by_date: dict[str, dict[str, dict]] = {}
    for dose in medication_days:
        total = dose.total if dose.total is not None else dose.taken
        status = dose.status or _medication_status(dose.taken, total)
        medication_by_date.setdefault(dose.date.isoformat(), {})[dose.med_key] = {
            "status": status,
            "taken": dose.taken,
            "total": total,
        }

    days_by_date: dict[str, dict] = {}
    for row in rows:
        for cell in row:
            if not cell:
                continue
            day_entries = entries_by_date.get(cell.iso, [])
            by_habit = {e.habit_key: e for e in day_entries}
            days_by_date[cell.iso] = {
                "date": cell.iso,
                "entries": day_entries,
                "by_habit": by_habit,
                "by_med": medication_by_date.get(cell.iso, {}),
                "metrics": _format_metrics(by_habit, metric_habits),
            }

    ordered = sorted(days_by_date)
    for i, iso in enumerate(ordered):
        d = date.fromisoformat(iso)
        day = days_by_date[iso]
        day["weekday_long"] = WEEKDAY_LONG[d.weekday()]
        day["month_day_long"] = d.strftime("%B ") + str(d.day)
        day["prev_iso"] = ordered[i - 1] if i > 0 else None
        day["next_iso"] = ordered[i + 1] if i < len(ordered) - 1 else None
    return days_by_date


def _clip_decimal_precision(text: str) -> str:
    """Keep decimal precision to at most two places for display."""
    if not text:
        return text

    def _replace(match: re.Match[str]) -> str:
        whole = match.group("int")
        frac = match.group("frac")[:2].rstrip("0")
        if not frac:
            return whole
        return f"{whole}.{frac}"

    return _LONG_DECIMAL_RE.sub(_replace, text)


def _for_render(entry: HabitEntry) -> HabitEntry:
    """Sanitize free-text fields used in the PDF without mutating stored data."""
    return entry.model_copy(
        update={
            "summary": _clip_decimal_precision(entry.summary),
            "description": _clip_decimal_precision(entry.description),
            "explanation": _clip_decimal_precision(entry.explanation),
        }
    )


def _format_metrics(by_habit: dict, metric_habits) -> str:
    """Format one day's metric-only habits for the page subtitle.

    Driven by the catalog's ``metric_only`` habits (e.g. sleep, recovery) rather
    than hard-coded keys, so adding a new metric habit needs no renderer change.
    Produces a bullet-separated line like "Sleep 7h42m · 89% · Recovery 78".
    """
    parts = []
    for h in metric_habits:
        entry = by_habit.get(h.key)
        if entry and entry.summary:
            parts.append(f"{h.label} {entry.summary}")
    return " · ".join(parts)


def _build_weeks(
    rows: list[list[CalendarCell]],
    days_by_date: dict[str, dict],
    habits,
) -> list[dict]:
    weeks: list[dict] = []
    for i, row in enumerate(rows, start=1):
        in_month = [c for c in row if c]
        if not in_month:
            continue
        first_d = date.fromisoformat(in_month[0].iso)
        last_d = date.fromisoformat(in_month[-1].iso)

        habit_counts: dict[str, int] = {}
        for h in habits:
            count = 0
            for cell in in_month:
                entry = days_by_date[cell.iso]["by_habit"].get(h.key)
                if entry and entry.status in ("checked", "partial", "manual"):
                    count += 1
            habit_counts[h.key] = count

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


_TALLY_FILLED_STATUSES = {"checked", "partial", "manual"}


def _build_tally(
    year: int,
    month: int,
    days_by_date: dict[str, dict],
    habits,
) -> list[dict]:
    """For each habit, build per-day fill data for the tally board page."""
    days_in_month = calendar.monthrange(year, month)[1]
    rows: list[dict] = []
    for h in habits:
        days = []
        filled_count = 0
        for day_num in range(1, days_in_month + 1):
            iso = date(year, month, day_num).isoformat()
            entry = days_by_date.get(iso, {}).get("by_habit", {}).get(h.key)
            is_filled = bool(entry and entry.status in _TALLY_FILLED_STATUSES)
            if is_filled:
                filled_count += 1
            days.append({"day": day_num, "iso": iso, "filled": is_filled})
        rows.append({
            "habit": h,
            "days": days,
            "filled_count": filled_count,
            "total_days": days_in_month,
        })
    return rows


def _medication_status(taken: int, total: int | None) -> str:
    expected = total if total is not None else taken
    if expected <= 0:
        return "taken" if taken > 0 else "none"
    if taken >= expected:
        return "taken"
    if taken > 0:
        return "partial"
    return "missed"


def _flatten_medications(med_groups) -> list[MedicationItem]:
    meds: list[MedicationItem] = []
    for group in med_groups:
        meds.extend(group.meds)
    return meds


def _build_med_tally(
    year: int,
    month: int,
    days_by_date: dict[str, dict],
    med_groups,
) -> list[dict]:
    """Build per-medication dose counts from logged medication day records.

    The denominator is based on days with explicit medication observations. This
    avoids rendering missing historical data as missed when the schedule was
    added after the fact. PRN meds only accrue possible doses on days they were
    logged.
    """
    rows: list[dict] = []
    for med in _flatten_medications(med_groups):
        days: list[dict] = []
        total_taken = 0
        total_possible = 0
        for day_num in range(1, calendar.monthrange(year, month)[1] + 1):
            iso = date(year, month, day_num).isoformat()
            logged = days_by_date.get(iso, {}).get("by_med", {}).get(med.key)
            if logged:
                taken = int(logged["taken"])
                total = int(logged["total"])
            else:
                taken = 0
                total = 0 if med.prn else 0
            total_taken += taken
            total_possible += total
            days.append({
                "day": day_num,
                "iso": iso,
                "taken": taken,
                "total": total,
                "filled": total > 0 and taken >= total,
                "partial": total > 0 and 0 < taken < total,
            })
        rows.append({
            "med": med,
            "days": days,
            "total_taken": total_taken,
            "total_possible": total_possible,
        })
    return rows



def _build_monthly_metrics(
    year: int,
    month: int,
    days_by_date: dict[str, dict],
    metric_habits,
) -> str:
    """Summarize metric-only coverage for the month, for the tally subtitle.

    Reports how many days carry each metric (e.g. "Sleep logged 30/31 ·
    Recovery logged 29/31"). Coverage avoids fragile parsing of free-text
    summaries while still giving an honest at-a-glance picture.
    """
    days_in_month = calendar.monthrange(year, month)[1]
    counts: dict[str, int] = {h.key: 0 for h in metric_habits}
    for day_num in range(1, days_in_month + 1):
        iso = date(year, month, day_num).isoformat()
        by_habit = days_by_date.get(iso, {}).get("by_habit", {})
        for h in metric_habits:
            entry = by_habit.get(h.key)
            if entry and entry.summary:
                counts[h.key] += 1

    parts = [
        f"{h.label} logged {counts[h.key]}/{days_in_month}"
        for h in metric_habits
        if counts[h.key] > 0
    ]
    return " · ".join(parts)


def render(state_or_path, out_dir: Path, today: date | None = None) -> Path:
    """Render a MonthHabitState (or a JSON path that loads into one) to PDF."""
    if isinstance(state_or_path, MonthHabitState):
        state = state_or_path
    else:
        state = load_month_state(state_or_path)

    year, month = (int(x) for x in state.month.split("-"))
    today = today or date.today()
    month_label = date(year, month, 1).strftime("%B %Y")

    # Metric-only habits (sleep, recovery) are computed and shown as context
    # next to each date, not as tracked cards in the grid/tally.
    card_habits = [h for h in state.habits if not h.metric_only]
    metric_habits = [h for h in state.habits if h.metric_only]

    rows = _build_calendar_rows(year, month, today)
    days_by_date = _build_days(rows, state.entries, metric_habits, state.medication_days)
    weeks = _build_weeks(rows, days_by_date, card_habits)
    tally_rows = _build_tally(year, month, days_by_date, card_habits)
    monthly_metrics = _build_monthly_metrics(year, month, days_by_date, metric_habits)
    med_tally_rows = _build_med_tally(year, month, days_by_date, state.medication_groups)

    # Attach week info to each day for the day-page nav.
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
        month_str=state.month,
        habits=card_habits,
        calendar_rows=rows,
        weeks=weeks,
        days=ordered_days,
        days_by_date=days_by_date,
        weekday_headers=WEEKDAY_HEADERS,
        status_glyph=STATUS_GLYPH,
        month_anchor=MONTH_ANCHOR,
        tally_anchor=TALLY_ANCHOR,
        med_tally_anchor=MED_TALLY_ANCHOR,
        tally_rows=tally_rows,
        med_groups=state.medication_groups,
        med_status_glyph=MED_STATUS_GLYPH,
        med_tally_rows=med_tally_rows,
        monthly_metrics=monthly_metrics,
    )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / f"{state.month}-habit-dashboard.pdf"
    (out_dir / f"{state.month}-habit-dashboard.html").write_text(html)
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
    p = argparse.ArgumentParser(description="Render a HabitOS monthly PDF for reMarkable 2.")
    p.add_argument("state_path", type=Path, help="Path to a MonthHabitState (or legacy month) JSON file")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/generated"),
        help="Directory to write the PDF into (default: data/generated)",
    )
    args = p.parse_args(argv)
    pdf = render(args.state_path, args.out_dir)
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
