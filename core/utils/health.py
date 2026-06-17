"""Programmatic health checks for the core runtime."""

from __future__ import annotations

import socket
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

import psycopg
import redis

from core.utils.settings import Settings, get_settings, validate_model_string


@dataclass(slots=True)
class HealthResult:
    name: str
    status: str
    detail: str
    required: bool = True


class HealthChecker:
    """Run required and optional system health checks."""

    def __init__(self, settings_factory: Callable[[], Settings] = get_settings) -> None:
        self.settings_factory = settings_factory

    def run(self) -> list[HealthResult]:
        checks: list[tuple[str, Callable[[], str], bool]] = [
            ("Environment", self.check_env, True),
            ("Model strings", self.check_models, True),
            ("PostgreSQL + pgvector", self.check_postgres, True),
            ("Redis", self.check_redis, True),
            ("Anthropic API", self.check_anthropic, True),
            ("OpenAI API", self.check_openai, False),
            ("LangSmith", self.check_langsmith, False),
        ]
        return [self._run_check(name, fn, required) for name, fn, required in checks]

    def failed_required(self, results: list[HealthResult]) -> list[HealthResult]:
        return [result for result in results if result.required and result.status == "fail"]

    def check_env(self) -> str:
        if not Path(".env").exists():
            raise ValueError(".env not found; copy .env.example to .env")
        return ".env present"

    def check_models(self) -> str:
        settings = self.settings_factory()
        for model in (
            settings.LLM_DEFAULT,
            settings.LLM_FAST,
            settings.LLM_POWERFUL,
            settings.LLM_EMBEDDINGS,
            settings.OPENAI_LLM_DEFAULT,
            settings.OPENAI_LLM_FAST,
            settings.OPENAI_LLM_FRONTIER,
        ):
            validate_model_string(model)
        return "all configured model strings valid"

    def check_postgres(self) -> str:
        settings = self.settings_factory()
        _assert_tcp_open(settings.DATABASE_URL, default_port=5432)
        with psycopg.connect(settings.DATABASE_URL, connect_timeout=1) as conn, conn.cursor() as cur:
            cur.execute("SELECT version()")
            version_row = cur.fetchone()
            version_text = str(version_row[0]) if version_row and version_row[0] else "unknown"
            version_parts = version_text.split()
            version = version_parts[1] if len(version_parts) > 1 else "unknown"
            cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
            pgvector = cur.fetchone()
        pgvector_version = pgvector[0] if pgvector and pgvector[0] else "missing"
        return f"postgres {version}; pgvector {pgvector_version}"

    def check_redis(self) -> str:
        settings = self.settings_factory()
        _assert_tcp_open(settings.REDIS_URL, default_port=6379)
        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        info = client.info("server")
        return f"redis {info['redis_version']}"

    def check_anthropic(self) -> str:
        settings = self.settings_factory()
        if settings.LLM_MODE == "mock":
            return "mock mode; key not required"
        key = settings.ANTHROPIC_API_KEY
        if not key or key in {"sk-ant-...", "sk-ant-api03-..."}:
            raise ValueError("ANTHROPIC_API_KEY not set")
        return "key configured"

    def check_openai(self) -> str:
        settings = self.settings_factory()
        key = settings.OPENAI_API_KEY
        if not key or key.startswith("sk-..."):
            raise ValueError("OPENAI_API_KEY not configured")
        return "key configured"

    def check_langsmith(self) -> str:
        settings = self.settings_factory()
        key = settings.LANGCHAIN_API_KEY
        if not key:
            raise ValueError("LANGCHAIN_API_KEY not configured")
        return "key configured"

    def _run_check(
        self,
        name: str,
        fn: Callable[[], str],
        required: bool,
    ) -> HealthResult:
        start = perf_counter()
        try:
            detail = fn()
            elapsed_ms = round((perf_counter() - start) * 1000)
            return HealthResult(name=name, status="pass", detail=f"{detail} ({elapsed_ms}ms)", required=required)
        except Exception as exc:
            status = "fail" if required else "warn"
            detail = _safe_error_detail(exc)
            return HealthResult(name=name, status=status, detail=detail, required=required)


def _safe_error_detail(exc: Exception) -> str:
    if isinstance(exc, ValueError) and "ANTHROPIC_API_KEY" in str(exc):
        return "ANTHROPIC_API_KEY is required unless LLM_MODE=mock"
    return str(exc)[:120]


def _assert_tcp_open(url: str, *, default_port: int) -> None:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return
    except OSError as exc:
        raise ConnectionError(f"{host}:{port} is not reachable") from exc
