"""HabitOS FastAPI application.

Run locally with:
    uvicorn apps.api.main:app --reload

Env vars (see .env.example): MONGODB_URI, MONGODB_DB_NAME, HABITOS_TIMEZONE,
optional HABITOS_OUTPUT_DIR / HABITOS_SAMPLE_EVENTS.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from packages.core.db import make_client
from packages.core.indexes import ensure_indexes

from apps.api.config import load_settings
from apps.api.routes import ROUTERS


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    client = make_client(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    await ensure_indexes(db)

    app.state.settings = settings
    app.state.client = client
    app.state.db = db
    app.state.output_dir = settings.output_dir
    app.state.sample_events_path = settings.sample_events_path

    try:
        yield
    finally:
        await client.close()


def create_app() -> FastAPI:
    app = FastAPI(title="HabitOS API", version="0.3.0", lifespan=lifespan)
    for router in ROUTERS:
        app.include_router(router)
    return app


app = create_app()
