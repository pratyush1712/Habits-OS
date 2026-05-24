"""Runtime configuration for the HabitOS API.

All settings are read from environment variables at app construction time.
No caching — env changes between app instances (e.g. across tests) take
effect immediately.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_EVENTS = REPO_ROOT / "data" / "sample_events.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "generated"


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_db_name: str
    habitos_timezone: str
    output_dir: Path
    sample_events_path: Path


def load_settings() -> Settings:
    return Settings(
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME", "habitos"),
        habitos_timezone=os.getenv("HABITOS_TIMEZONE", "UTC"),
        output_dir=Path(os.getenv("HABITOS_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR))),
        sample_events_path=Path(
            os.getenv("HABITOS_SAMPLE_EVENTS", str(DEFAULT_SAMPLE_EVENTS))
        ),
    )
