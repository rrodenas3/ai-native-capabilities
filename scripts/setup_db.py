#!/usr/bin/env python3
"""Idempotent PostgreSQL database setup."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.utils.settings import get_settings  # noqa: E402


def database_url(test: bool = False) -> str:
    try:
        resolved_url = get_settings().DATABASE_URL
    except ValueError:
        resolved_url = os.getenv(
            "DATABASE_URL",
            "postgresql://localhost:5432/ai_native",
        )
    if not test:
        return resolved_url
    parts = conninfo_to_dict(resolved_url)
    dbname = parts.get("dbname") or "ai_native"
    parts["dbname"] = f"{dbname}_test" if not dbname.endswith("_test") else dbname
    return make_conninfo(**parts)


def admin_url(target_url: str) -> str:
    parts = conninfo_to_dict(target_url)
    parts["dbname"] = "postgres"
    return make_conninfo(**parts)


def ensure_database(target_url: str) -> None:
    target = conninfo_to_dict(target_url).get("dbname")
    if not target:
        raise ValueError("DATABASE_URL must include a database name")
    with psycopg.connect(admin_url(target_url), autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,))
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))


def apply_schema(target_url: str) -> None:
    schema_path = ROOT / "scripts" / "init_db.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Database schema file not found: {schema_path}")
    schema_sql = schema_path.read_text(encoding="utf-8")
    with psycopg.connect(target_url) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()


def setup_database(*, test: bool = False) -> str:
    target_url = database_url(test=test)
    ensure_database(target_url)
    apply_schema(target_url)
    return target_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up ai-native-capabilities database")
    parser.add_argument("--test", action="store_true", help="Create/use ai_native_test")
    args = parser.parse_args()

    target = setup_database(test=args.test)
    print(f"Database setup complete: {conninfo_to_dict(target).get('dbname')}")


if __name__ == "__main__":
    main()
