from __future__ import annotations

import os

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from core.utils.db import get_connection, get_pool
from scripts.setup_db import apply_schema, database_url, ensure_database

REQUIRED_COLUMNS = {
    "episodic_memory": {
        "id",
        "capability",
        "session_id",
        "run_id",
        "event_type",
        "content",
        "embedding",
        "metadata",
        "created_at",
    },
    "document_chunks": {
        "id",
        "capability",
        "doc_id",
        "chunk_index",
        "content",
        "embedding",
        "metadata",
        "access_tier",
        "created_at",
    },
    "audit_trail": {
        "id",
        "capability",
        "run_id",
        "session_id",
        "event_type",
        "agent_name",
        "action",
        "payload",
        "decision",
        "approved_by",
        "cost_usd",
        "created_at",
    },
    "langgraph_checkpoints": {
        "thread_id",
        "checkpoint_ns",
        "checkpoint_id",
        "parent_id",
        "type",
        "checkpoint",
        "metadata",
        "created_at",
    },
}


def db_available() -> bool:
    try:
        with psycopg.connect(database_url(test=True), connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


requires_db = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1" and not db_available(),
    reason="PostgreSQL test database is not available",
)


@requires_db
def test_setup_db_is_idempotent(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    target = database_url(test=True)

    ensure_database(target)
    apply_schema(target)
    apply_schema(target)

    with psycopg.connect(target) as conn, conn.cursor() as cur:
        cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')")
        assert {row[0] for row in cur.fetchall()} == {"vector", "pg_trgm"}


@requires_db
def test_core_table_schemas_exist(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    target = database_url(test=True)
    ensure_database(target)
    apply_schema(target)

    with psycopg.connect(target, row_factory=dict_row) as conn, conn.cursor() as cur:
        for table, expected_columns in REQUIRED_COLUMNS.items():
            cur.execute(
                """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    """,
                (table,),
            )
            columns = {row["column_name"] for row in cur.fetchall()}
            assert expected_columns <= columns


@requires_db
def test_audit_trail_public_update_delete_revoked(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    target = database_url(test=True)
    ensure_database(target)
    apply_schema(target)

    with psycopg.connect(target) as conn, conn.cursor() as cur:
        cur.execute("SELECT has_table_privilege('PUBLIC', 'audit_trail', 'UPDATE')")
        assert cur.fetchone()[0] is False
        cur.execute("SELECT has_table_privilege('PUBLIC', 'audit_trail', 'DELETE')")
        assert cur.fetchone()[0] is False


def test_get_connection_uses_database_url(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")

    assert get_connection is not None


def test_get_pool_returns_async_pool(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    pool = get_pool("postgresql://postgres:postgres@localhost:5432/ai_native_test")

    assert isinstance(pool, AsyncConnectionPool)

