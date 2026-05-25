"""Runtime configuration for the HabitOS API.

All settings are read from environment variables at app construction time.
No caching — env changes between app instances (e.g. across tests) take
effect immediately.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import find_dotenv, load_dotenv

from packages.connectors.dayone.config import DayOneSettings, load_dayone_settings


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
class RemarkableSettings:
    adapter: Literal["manual", "rmapi"]
    rmapi_binary: str
    rmapi_config_path: str
    rmapi_timeout_seconds: int
    rmapi_trace: bool
    rmapi_replace_existing_current: bool
    machine_root: str


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_db_name: str
    habitos_timezone: str
    output_dir: Path
    sample_events_path: Path
    scheduler_enabled: bool
    nightly_run_hour: int
    nightly_run_minute: int
    reconcile_days: int
    default_whoop_external_user_id: str
    auto_upload_remarkable: bool
    remarkable_dry_run: bool
    whoop: WhoopSettings
    remarkable: RemarkableSettings
    dayone: DayOneSettings


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
        scheduler_enabled=_env_bool("HABITOS_SCHEDULER_ENABLED", default=False),
        nightly_run_hour=_env_int("HABITOS_NIGHTLY_RUN_HOUR", default=3, minimum=0, maximum=23),
        nightly_run_minute=_env_int(
            "HABITOS_NIGHTLY_RUN_MINUTE", default=0, minimum=0, maximum=59
        ),
        reconcile_days=_env_int("HABITOS_RECONCILE_DAYS", default=14, minimum=1),
        default_whoop_external_user_id=os.getenv("HABITOS_DEFAULT_WHOOP_EXTERNAL_USER_ID", ""),
        auto_upload_remarkable=_env_bool("HABITOS_AUTO_UPLOAD_REMARKABLE", default=False),
        remarkable_dry_run=_env_bool("HABITOS_REMARKABLE_DRY_RUN", default=True),
        remarkable=RemarkableSettings(
            adapter=_env_choice(
                "HABITOS_REMARKABLE_ADAPTER",
                default="manual",
                allowed=("manual", "rmapi"),
            ),
            rmapi_binary=os.getenv("HABITOS_RMAPI_BINARY", "rmapi"),
            rmapi_config_path=os.getenv("HABITOS_RMAPI_CONFIG_PATH", ""),
            rmapi_timeout_seconds=_env_int(
                "HABITOS_RMAPI_TIMEOUT_SECONDS", default=60, minimum=1
            ),
            rmapi_trace=_env_bool("HABITOS_RMAPI_TRACE", default=False),
            rmapi_replace_existing_current=_env_bool(
                "HABITOS_RMAPI_REPLACE_EXISTING_CURRENT", default=False
            ),
            machine_root=os.getenv("HABITOS_REMARKABLE_MACHINE_ROOT", "HabitOS"),
        ),
        dayone=load_dayone_settings(),
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


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean-like value, got {raw!r}")


def _env_choice(name: str, *, default: str, allowed: tuple[str, ...]) -> str:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value not in allowed:
        raise ValueError(
            f"{name} must be one of {allowed!r}, got {raw!r}"
        )
    return value


def _env_int(
    name: str,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        value = default
    else:
        value = int(raw)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}, got {value}")
    return value
