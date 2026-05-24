"""Fixtures for repository integration tests.

Tests that ask for the `db` fixture skip automatically when MONGODB_TEST_URI
is unset, so the suite stays green for contributors without a local Mongo.

Each test gets its own freshly-named database, dropped on teardown — no risk
of leftover state between tests and no risk of clobbering real data.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

from packages.core.db import make_client

from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

TEST_URI_ENV = "MONGODB_TEST_URI"


@pytest_asyncio.fixture
async def db():
    uri = os.getenv(TEST_URI_ENV)
    if not uri:
        pytest.skip(f"set {TEST_URI_ENV} to run repository integration tests")

    client = make_client(uri)
    db_name = f"habitos_test_{uuid.uuid4().hex[:10]}"
    try:
        yield client[db_name]
    finally:
        await client.drop_database(db_name)
        await client.close()
