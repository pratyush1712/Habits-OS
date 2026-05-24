"""Runtime configuration for the HabitOS API.

All settings are read from environment variables at app construction time.
No caching — env changes between app instances (e.g. across tests) take
effect immediately.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_EVENTS = REPO_ROOT / "data" / "sample_events.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "generated"

load_dotenv(find_dotenv())


@dataclass(frozen=True)
class WhoopSettings:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...]
    api_base_url: str
    auth_url: str
    token_url: str
    webhook_secret: str


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_db_name: str
    habitos_timezone: str
    output_dir: Path
    sample_events_path: Path
    whoop: WhoopSettings


def load_settings() -> Settings:
    whoop_scopes = tuple(
        scope
        for scope in os.getenv(
            "WHOOP_SCOPES",
            "offline read:workout read:sleep read:recovery read:profile",
        ).split()
        if scope
    )
    return Settings(
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME", "habitos"),
        habitos_timezone=os.getenv("HABITOS_TIMEZONE", "UTC"),
        output_dir=Path(os.getenv("HABITOS_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR))),
        sample_events_path=Path(
            os.getenv("HABITOS_SAMPLE_EVENTS", str(DEFAULT_SAMPLE_EVENTS))
        ),
        whoop=WhoopSettings(
            client_id=os.getenv("WHOOP_CLIENT_ID", ""),
            client_secret=os.getenv("WHOOP_CLIENT_SECRET", ""),
            redirect_uri=os.getenv(
                "WHOOP_REDIRECT_URI",
                "http://localhost:8000/whoop/oauth/callback",
            ),
            scopes=whoop_scopes,
            api_base_url=os.getenv(
                "WHOOP_API_BASE_URL",
                "https://api.prod.whoop.com/developer",
            ),
            auth_url=os.getenv(
                "WHOOP_AUTH_URL",
                "https://api.prod.whoop.com/oauth/oauth2/auth",
            ),
            token_url=os.getenv(
                "WHOOP_TOKEN_URL",
                "https://api.prod.whoop.com/oauth/oauth2/token",
            ),
            webhook_secret=os.getenv("WHOOP_WEBHOOK_SECRET", ""),
        ),
    )
