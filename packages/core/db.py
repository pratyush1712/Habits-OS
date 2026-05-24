"""MongoDB connection management.

Async client lifecycle is intentionally simple: callers construct an
`AsyncMongoClient`, hold it for the lifetime of the app (or test), and close
it on shutdown. FastAPI's lifespan handler can call `make_client` /
`client.close()` directly when M3 lands.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from pymongo import AsyncMongoClient

from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())


DEFAULT_URI = os.getenv("MONGODB_URI")
DEFAULT_DB_NAME = os.getenv("MONGODB_DB_NAME", "Habit-OS")


def get_mongo_uri() -> str:
    return DEFAULT_URI


def get_db_name() -> str:
    return DEFAULT_DB_NAME


def make_client(uri: str | None = None) -> AsyncMongoClient:
    """Build an AsyncMongoClient. Caller is responsible for closing it.

    `tz_aware=True` ensures BSON ISODate values are returned as tz-aware UTC
    `datetime` objects on read — matching how the application stores them and
    keeping round-trips lossless.
    """
    return AsyncMongoClient(uri or get_mongo_uri(), tz_aware=True)


def get_db(client: AsyncMongoClient, name: str | None = None):
    return client[name or get_db_name()]


@asynccontextmanager
async def lifespan_client(uri: str | None = None) -> AsyncIterator[AsyncMongoClient]:
    """Async context manager — convenient for tests and short-lived scripts."""
    client = make_client(uri)
    try:
        yield client
    finally:
        await client.close()
