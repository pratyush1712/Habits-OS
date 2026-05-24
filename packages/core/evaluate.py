"""CLI: run the rule engine against an events JSON, write state, render PDF.

Usage:
    python -m packages.core.evaluate data/sample_events.json
    python -m packages.core.evaluate data/sample_events.json --state-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from packages.core.config import DEFAULT_RULES
from packages.core.rules import evaluate_month
from packages.renderer.state_loader import load_events_input


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Evaluate source events into a MonthHabitState and render the PDF."
    )
    p.add_argument("events_path", type=Path, help="Path to an events JSON file")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/generated"),
        help="Directory to write the state JSON and PDF into (default: data/generated)",
    )
    p.add_argument(
        "--state-only",
        action="store_true",
        help="Write the MonthHabitState JSON only; skip PDF rendering.",
    )
    args = p.parse_args(argv)

    month, habits, events, overrides = load_events_input(args.events_path)
    state = evaluate_month(month, habits, events, overrides, DEFAULT_RULES)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.out_dir / f"{month}-state.json"
    state_path.write_text(state.model_dump_json(indent=2))
    print(f"Wrote state: {state_path}")

    if not args.state_only:
        # Late import: keeps the rule engine importable without playwright.
        from packages.renderer.render_month import render

        pdf = render(state_path, args.out_dir)
        print(f"Wrote PDF:   {pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
