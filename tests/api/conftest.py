"""Test fixtures for the FastAPI app.

Each test gets a freshly-named Mongo database that is dropped on teardown,
and PDFs render into a per-test tmp_path so we never write to data/generated.

Tests skip automatically when MONGODB_TEST_URI is unset.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient


TEST_URI_ENV = "MONGODB_TEST_URI"


@pytest_asyncio.fixture
async def api_client(tmp_path, monkeypatch):
    uri = os.getenv(TEST_URI_ENV)
    if not uri:
        pytest.skip(f"set {TEST_URI_ENV} to run API integration tests")

    db_name = f"habitos_api_test_{uuid.uuid4().hex[:10]}"
    monkeypatch.setenv("MONGODB_URI", uri)
    monkeypatch.setenv("MONGODB_DB_NAME", db_name)
    monkeypatch.setenv("HABITOS_OUTPUT_DIR", str(tmp_path))

    # Import after env is set so the lifespan picks up our overrides.
    from apps.api.main import create_app

    app = create_app()

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    cleanup = AsyncMongoClient(uri)
    try:
        await cleanup.drop_database(db_name)
    finally:
        await cleanup.close()
