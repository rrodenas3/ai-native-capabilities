#!/usr/bin/env python3
"""
Check eval gates - enforces blocking metrics from capability specs.
Called by GitHub Actions CI after each capability eval run.

Usage:
    python scripts/check_eval_gates.py reports/cap-01.json --capability cap-01
    python scripts/check_eval_gates.py reports/cap-04.json --capability cap-04
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from core.evals.gate_config import (
    BLOCKING_METRICS,
    WARNING_THRESHOLDS,
    check_metric,
    evaluate_report,
    is_enforced_cap,
)


def fmt(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return f"{v:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check capability eval gates")
    parser.add_argument("report", help="Path to eval report JSON")
    parser.add_argument("--capability", required=True, help="Capability ID (e.g. cap-01)")
    args = parser.parse_args()

    report_path = Path(args.report)
    cap_id = args.capability

    if not report_path.exists():
        print(f"ERROR: report not found at {report_path}")
        if is_enforced_cap(cap_id):
            print(f"[{cap_id}] Enforced capability — missing eval report blocks merge")
            sys.exit(1)
        print("This usually means the eval suite has not been implemented yet.")
        print("Create cap-XX/evals/suite.py to fix this.")
        sys.exit(0)

    with open(report_path) as f:
        report = json.load(f)

    evaluation = evaluate_report(report, cap_id)
    metrics = report.get("metrics", {})

    if evaluation.fatal_status:
        note = evaluation.fatal_note or ""
        print(f"[{cap_id}] Eval suite status: {evaluation.fatal_status}")
        if note:
            print(f"  Note: {note}")
        if is_enforced_cap(cap_id):
            print("  BLOCKING — enforced capability requires a passing eval suite")
            sys.exit(1)
        print("  Skipping gate check - eval suite not yet implemented")
        sys.exit(0)

    blocking = BLOCKING_METRICS.get(cap_id, [])
    warnings = WARNING_THRESHOLDS.get(cap_id, [])
    failures = evaluation.failures
    warns = evaluation.warnings

    if HAS_RICH:
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
        table.add_column("Metric", width=38)
        table.add_column("Value", justify="right", width=10)
        table.add_column("Target", justify="right", width=10)
        table.add_column("Result", width=10)

        for m, t, lib in blocking:
            val = metrics.get(m, None)
            if val is None:
                result = "[red]MISSING[/red]"
                val_str = "[dim]-[/dim]"
            elif check_metric(val, t, lib):
                result = "[green]PASS[/green]"
                val_str = f"[green]{fmt(val)}[/green]"
            else:
                result = "[red]BLOCK[/red]"
                val_str = f"[red]{fmt(val)}[/red]"

            op = "<=" if lib else ">="
            table.add_row(f"[bold]{m}[/bold]", val_str, f"{op} {fmt(t)}", result)

        for m, t, lib in warnings:
            val = metrics.get(m, None)
            if val is None:
                continue
            if check_metric(val, t, lib):
                result = "[green]PASS[/green]"
                val_str = f"[dim]{fmt(val)}[/dim]"
            else:
                result = "[yellow]WARN[/yellow]"
                val_str = f"[yellow]{fmt(val)}[/yellow]"

            op = "<=" if lib else ">="
            table.add_row(m, val_str, f"{op} {fmt(t)}", result)

        console.print(f"\n[bold]{cap_id} - Eval Gates[/bold]")
        console.print(table)
    else:
        print(f"\n{cap_id} - Eval Gates")
        for m, t, lib in blocking:
            val = metrics.get(m, "MISSING")
            op = "<=" if lib else ">="
            status_str = "BLOCK" if isinstance(val, float) and not check_metric(val, t, lib) else "PASS"
            print(f"  [BLOCKING] {m}: {val} (target {op} {t}) -> {status_str}")

    if failures:
        op_map = {True: "<=", False: ">="}
        fail_lines = []
        for m, v, t, lib in failures:
            op = op_map[lib]
            got = "MISSING" if v == -1.0 else fmt(v)
            fail_lines.append(f"  - {m}: got {got}, need {op} {t}")

        msg = f"\n[{cap_id}] BLOCKING METRICS FAILED - PR cannot be merged\n"
        msg += "\n".join(fail_lines)

        if HAS_RICH:
            console.print(f"\n[red bold]{msg}[/red bold]\n")
        else:
            print(msg)

        sys.exit(1)

    if warns:
        if HAS_RICH:
            console.print(f"\n[yellow][{cap_id}] {len(warns)} warning(s) - fix before next release[/yellow]\n")
        else:
            print(f"\n[{cap_id}] WARNINGS: {len(warns)} non-blocking issues")

    if HAS_RICH:
        console.print(f"[green bold][{cap_id}] All blocking gates passed[/green bold]\n")
    else:
        print(f"\n[{cap_id}] All blocking gates passed")


if __name__ == "__main__":
    main()
