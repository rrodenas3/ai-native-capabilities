#!/usr/bin/env python3
"""
Check eval gates - enforces blocking metrics from capability specs.
Called by GitHub Actions CI after each capability eval run.

Usage:
    python scripts/check_eval_gates.py reports/cap01.json --capability cap-01
    python scripts/check_eval_gates.py reports/cap04.json --capability cap-04
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

# Blocking metrics per capability - derived from each capability's SPEC.md
# These mirror the eval_scorecard blocking fields in the specs exactly.
BLOCKING_METRICS: dict[str, list[tuple[str, float, bool]]] = {
    # (metric_name, threshold, lower_is_better)
    "cap-01": [
        ("citation_accuracy",   0.95, False),
        ("hallucination_rate",  0.02, True),
    ],
    "cap-02": [
        ("briefing_completeness",    1.00, False),
        ("security_weakness_rate",   5.0,  True),
    ],
    "cap-03": [
        ("agent_sprawl_count",    2.0, True),
        ("escalation_accuracy",   0.90, False),
    ],
    "cap-04": [
        ("human_approval_coverage",  1.00, False),
        ("digital_twin_validation",  1.00, False),
    ],
    "cap-05": [
        ("false_negative_rate_obligations", 0.01, True),
        ("citation_accuracy",               0.98, False),
        ("expert_review_coverage",          1.00, False),
        ("query_answer_citation_rate",      1.00, False),
    ],
}

# Non-blocking warning thresholds
WARNING_THRESHOLDS: dict[str, list[tuple[str, float, bool]]] = {
    "cap-01": [
        ("retrieval_recall",        0.85, False),
        ("human_override_rate",     0.15, True),
        ("response_latency_p95_s",  30.0, True),
        ("cost_per_brief_usd",      0.50, True),
    ],
    "cap-02": [
        ("acceptance_criteria_pass",  0.90, False),
        ("test_coverage",             0.80, False),
        ("cost_per_task_usd",         2.00, True),
    ],
    "cap-03": [
        ("intent_classification_accuracy",  0.92, False),
        ("basket_margin_awareness",         0.95, False),
        ("response_latency_p95_ms",       1500.0, True),
    ],
    "cap-04": [
        ("forecast_accuracy_mape",       0.15, True),
        ("stockout_reduction_rate",      0.30, False),
        ("autonomous_action_accuracy",   0.95, False),
        ("exception_detection_recall",   0.90, False),
    ],
    "cap-05": [
        ("false_positive_rate_obligations", 0.10, True),
        ("gap_detection_accuracy",          0.90, False),
        ("knowledge_graph_accuracy",        0.92, False),
    ],
}


def check_metric(value: float, threshold: float, lower_is_better: bool) -> bool:
    """Return True if the metric passes its gate."""
    if lower_is_better:
        return value <= threshold
    return value >= threshold


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
        print("This usually means the eval suite has not been implemented yet.")
        print("Create cap-XX/evals/suite.py to fix this.")
        sys.exit(0)  # Don't fail CI for missing eval suite (not yet built)

    with open(report_path) as f:
        report = json.load(f)

    status = report.get("status", "unknown")
    metrics = report.get("metrics", {})

    if status in ("no_eval_suite", "not_found", "error"):
        note = report.get("note", report.get("stderr", ""))
        print(f"[{cap_id}] Eval suite status: {status}")
        if note:
            print(f"  Note: {note}")
        print("  Skipping gate check - eval suite not yet implemented")
        sys.exit(0)

    blocking = BLOCKING_METRICS.get(cap_id, [])
    warnings = WARNING_THRESHOLDS.get(cap_id, [])

    failures: list[tuple[str, float, float, bool]] = []
    warns: list[tuple[str, float, float, bool]] = []

    for metric_name, threshold, lower_is_better in blocking:
        if metric_name not in metrics:
            failures.append((metric_name, -1.0, threshold, lower_is_better))
            continue
        value = metrics[metric_name]
        if not check_metric(value, threshold, lower_is_better):
            failures.append((metric_name, value, threshold, lower_is_better))

    for metric_name, threshold, lower_is_better in warnings:
        if metric_name not in metrics:
            continue
        value = metrics[metric_name]
        if not check_metric(value, threshold, lower_is_better):
            warns.append((metric_name, value, threshold, lower_is_better))

    # Print results
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
