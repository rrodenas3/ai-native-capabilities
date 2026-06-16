#!/usr/bin/env python3
"""
ai-native-capabilities setup script.
Run once after cloning: python scripts/setup.py
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    print(f"  → {cmd}")
    return subprocess.run(cmd, shell=True, check=check, cwd=ROOT)


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main() -> None:
    test_mode = "--test" in sys.argv

    section("1 / 5  Environment check")
    py = sys.version_info
    assert py >= (3, 12), f"Python 3.12+ required, got {py.major}.{py.minor}"
    print(f"  ✓ Python {py.major}.{py.minor}.{py.micro}")

    env_file = ROOT / ".env"
    if not env_file.exists():
        run(f"cp {ROOT}/.env.example {ROOT}/.env")
        print("  ✓ .env created from .env.example — add your API keys")
    else:
        print("  ✓ .env already exists")

    section("2 / 5  Python dependencies")
    run("pip install -e '.[dev]' -q")
    print("  ✓ dependencies installed")

    section("3 / 5  Docker services")
    run("docker compose up -d postgres redis", check=False)
    run("docker compose ps")

    section("4 / 5  Database setup")
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/ai_native"
        + ("_test" if test_mode else ""),
    )
    print(f"  Database: {db_url.split('@')[1] if '@' in db_url else db_url}")

    # Wait for postgres
    import time
    for attempt in range(20):
        result = run(
            f"psql {db_url} -c 'SELECT 1' -q 2>/dev/null", check=False
        )
        if result.returncode == 0:
            break
        print(f"  Waiting for postgres... ({attempt + 1}/20)")
        time.sleep(2)

    run(f"psql {db_url} -c 'CREATE EXTENSION IF NOT EXISTS vector'")
    print("  ✓ pgvector extension enabled")

    section("5 / 5  Health check")
    run("python scripts/health_check.py")

    print("\n" + "═" * 60)
    print("  ✓ Setup complete!")
    print()
    print("  Quick start:")
    print("    python cap-01-decision-intelligence/demo.py")
    print()
    print("  Run all evals:")
    print("    python scripts/run_evals.py --all")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
