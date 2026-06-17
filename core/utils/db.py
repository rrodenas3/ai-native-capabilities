"""Database connection utilities."""

from __future__ import annotations

import psycopg
from psycopg import Connection
from psycopg_pool import AsyncConnectionPool

from core.utils.settings import get_settings


def get_connection(database_url: str | None = None) -> Connection:
    try:
        return psycopg.connect(database_url or get_settings().DATABASE_URL)
    except Exception as exc:
        raise ConnectionError("Unable to connect to configured PostgreSQL database") from exc


def get_pool(database_url: str | None = None, *, open: bool = False) -> AsyncConnectionPool:
    try:
        return AsyncConnectionPool(conninfo=database_url or get_settings().DATABASE_URL, open=open)
    except Exception as exc:
        raise ConnectionError("Unable to create configured PostgreSQL connection pool") from exc

