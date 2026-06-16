#!/usr/bin/env python3
"""
Health check — verifies all services and API connections are alive.
Run: python scripts/health_check.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from rich.console import Console
from rich.table import Table

console = Console()


def check(name: str, fn) -> tuple[str, str, str]:
    try:
        msg = fn()
        return name, "✓", msg or "ok"
    except Exception as e:
        return name, "✗", str(e)[:60]


def check_postgres() -> str:
    import psycopg
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/ai_native")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            ver = cur.fetchone()[0].split(" ")[1]
            cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
            pgv = cur.fetchone()
    return f"postgres {ver} · pgvector {pgv[0] if pgv else 'NOT installed'}"


def check_redis() -> str:
    import redis
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    r.ping()
    info = r.info("server")
    return f"redis {info['redis_version']}"


def check_anthropic() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-ant-..."):
        raise ValueError("ANTHROPIC_API_KEY not set")
    return f"key set ({key[:12]}...)"


def check_openai() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key.startswith("sk-..."):
        raise ValueError("OPENAI_API_KEY not set")
    return f"key set ({key[:8]}...)"


def check_langsmith() -> str:
    key = os.getenv("LANGCHAIN_API_KEY", "")
    if not key:
        return "not configured (optional)"
    return f"key set ({key[:12]}...)"


def check_env() -> str:
    env_file = Path(".env")
    if not env_file.exists():
        raise ValueError(".env not found — run: cp .env.example .env")
    return ".env present"


def main() -> None:
    console.print("\n[bold]ai-native-capabilities — health check[/bold]\n")

    checks = [
        ("Environment", check_env),
        ("PostgreSQL + pgvector", check_postgres),
        ("Redis", check_redis),
        ("Anthropic API", check_anthropic),
        ("OpenAI API", check_openai),
        ("LangSmith", check_langsmith),
    ]

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Service", style="dim", width=28)
    table.add_column("Status", width=4)
    table.add_column("Detail")

    results = [check(name, fn) for name, fn in checks]
    failed = []

    for name, status, detail in results:
        color = "green" if status == "✓" else "red"
        table.add_row(name, f"[{color}]{status}[/{color}]", detail)
        if status == "✗":
            failed.append(name)

    console.print(table)

    if failed:
        console.print(f"\n[red]✗ {len(failed)} check(s) failed: {', '.join(failed)}[/red]")
        console.print("[dim]See .env.example and docker-compose.yml for setup instructions[/dim]\n")
        sys.exit(1)
    else:
        console.print("\n[green]✓ All systems operational[/green]\n")


if __name__ == "__main__":
    main()
