"""Anchor helpers — keep link naming centralised so templates and renderer agree."""

from __future__ import annotations


MONTH_ANCHOR = "month"
TALLY_ANCHOR = "tally"


def day_anchor(iso_date: str) -> str:
    return f"day-{iso_date}"


def week_anchor(index: int) -> str:
    """Anchor for a week's Plan page (start-of-week, intention setting)."""
    return f"week-{index}"


def week_review_anchor(index: int) -> str:
    """Anchor for a week's Review page (end-of-week, reflection)."""
    return f"week-{index}-review"
