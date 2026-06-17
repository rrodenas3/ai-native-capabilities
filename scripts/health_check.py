#!/usr/bin/env python3
"""Health check CLI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from rich.console import Console
from rich.table import Table

from core.utils.health import HealthChecker

console = Console()

def main() -> None:
    checker = HealthChecker()
    results = checker.run()
    failed = checker.failed_required(results)

    console.print("\n[bold]ai-native-capabilities - health check[/bold]\n")
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Service", style="dim", width=28)
    table.add_column("Status", width=8)
    table.add_column("Required", width=9)
    table.add_column("Detail")

    for result in results:
        color = {"pass": "green", "warn": "yellow", "fail": "red"}[result.status]
        table.add_row(
            result.name,
            f"[{color}]{result.status.upper()}[/{color}]",
            "yes" if result.required else "optional",
            result.detail,
        )

    console.print(table)
    if failed:
        console.print(
            "\n[red]Required checks failed: "
            + ", ".join(result.name for result in failed)
            + "[/red]"
        )
        console.print("[dim]See .env.example and docker-compose.yml for setup instructions[/dim]\n")
        sys.exit(1)

    console.print("\n[green]All required checks passed[/green]\n")


if __name__ == "__main__":
    main()
