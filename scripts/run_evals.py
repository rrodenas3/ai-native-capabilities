#!/usr/bin/env python3
"""
Unified eval runner for all capabilities.

Usage:
    python scripts/run_evals.py --all              # run all 5 capabilities
    python scripts/run_evals.py --cap cap-01       # single capability
    python scripts/run_evals.py --all --mock       # use mock LLMs (no API cost)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from core.evals.gate_config import evaluate_report

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box as rich_box
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

ROOT = Path(__file__).parent.parent
CAPS = ["cap-01", "cap-02", "cap-03", "cap-04", "cap-05"]
CAP_NAMES = {
    "cap-01": "Decision Intelligence",
    "cap-02": "Agentic Engineering",
    "cap-03": "Agentic Commerce",
    "cap-04": "Autonomous Operations",
    "cap-05": "Compliance Intelligence",
}


def run_cap_evals(cap_id: str, mock: bool = True) -> dict:
    cap_dir = ROOT / f"{cap_id}-*"
    import glob
    matches = glob.glob(str(cap_dir))
    if not matches:
        return {"cap": cap_id, "status": "not_found", "score": 0.0, "blocking_failures": []}

    cap_path = Path(matches[0])
    eval_script = cap_path / "evals" / "suite.py"
    report_path = ROOT / "reports" / f"{cap_id}.json"
    report_path.parent.mkdir(exist_ok=True)

    if not eval_script.exists():
        report = {
            "cap": cap_id,
            "status": "no_eval_suite",
            "score": 0.0,
            "note": f"eval suite not yet implemented at {eval_script}",
        }
        gate = evaluate_report(report, cap_id)
        report["blocking_failures"] = gate.failure_names
        return report

    env = {
        "EVAL_MODE": "ci",
        "LLM_MODE": "mock" if mock else "real",
        "REQUIRE_SECURITY_SCANNERS": "1",
    }
    full_env = {**os.environ, **env}

    start = time.time()
    result = subprocess.run(
        [sys.executable, str(eval_script), "--output", str(report_path)],
        cwd=ROOT,
        env=full_env,
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - start

    if report_path.exists():
        with open(report_path) as f:
            report = json.load(f)
        report["elapsed_s"] = round(elapsed, 1)
        gate = evaluate_report(report, cap_id)
        report["blocking_failures"] = gate.failure_names
        return report

    report = {
        "cap": cap_id,
        "status": "error",
        "score": 0.0,
        "stderr": result.stderr[:200],
        "elapsed_s": round(elapsed, 1),
    }
    gate = evaluate_report(report, cap_id)
    report["blocking_failures"] = gate.failure_names
    return report


def print_summary(results: list[dict]) -> None:
    if not HAS_RICH:
        for r in results:
            print(f"{r['cap']}: {r.get('status', '?')} score={r.get('score', 0):.2f}")
        return

    table = Table(
        title="\nEval Results — ai-native-capabilities",
        box=rich_box.SIMPLE_HEAVY,
        show_footer=True,
    )
    table.add_column("Capability", style="bold", footer="")
    table.add_column("Score", justify="right", footer="")
    table.add_column("Status", footer="")
    table.add_column("Blocking failures", footer="")
    table.add_column("Time", justify="right", footer="")

    all_pass = True
    for r in results:
        cap_id = r.get("cap", "?")
        score = r.get("score", 0.0)
        status = r.get("status", "?")
        blocking = r.get("blocking_failures", [])
        elapsed = r.get("elapsed_s", 0.0)
        note = r.get("note", "")

        if status in ("no_eval_suite", "not_found"):
            status_display = f"[dim]{status}[/dim]"
            score_display = "[dim]—[/dim]"
            blocking_display = f"[dim]{note or ''}[/dim]"
        elif blocking:
            status_display = "[red]FAIL[/red]"
            score_display = f"[red]{score:.2f}[/red]"
            blocking_display = "[red]" + ", ".join(blocking) + "[/red]"
            all_pass = False
        elif score >= 0.85:
            status_display = "[green]PASS[/green]"
            score_display = f"[green]{score:.2f}[/green]"
            blocking_display = "[dim]none[/dim]"
        else:
            status_display = "[yellow]WARN[/yellow]"
            score_display = f"[yellow]{score:.2f}[/yellow]"
            blocking_display = "[yellow]score below threshold[/yellow]"
            all_pass = False

        table.add_row(
            f"{cap_id}  [dim]{CAP_NAMES.get(cap_id, '')}[/dim]",
            score_display,
            status_display,
            blocking_display,
            f"[dim]{elapsed}s[/dim]",
        )

    console.print(table)

    if all_pass:
        console.print("[green bold]PASS: All eval gates passed -- ready to merge[/green bold]\n")
    else:
        console.print("[red bold]FAIL: Eval gates failed -- fix before merging[/red bold]\n")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run eval suites")
    parser.add_argument("--all", action="store_true", help="Run all capabilities")
    parser.add_argument("--cap", help="Run single capability (e.g. cap-01)")
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock LLMs")
    parser.add_argument("--real", action="store_true", help="Use real LLMs (costs money)")
    args = parser.parse_args()

    use_mock = not args.real

    if args.all:
        caps = CAPS
    elif args.cap:
        caps = [args.cap]
    else:
        parser.print_help()
        sys.exit(1)

    if HAS_RICH:
        console.print(
            f"\n[bold]Running evals[/bold] for: {', '.join(caps)} "
            f"({'mock' if use_mock else 'real'} LLMs)\n"
        )

    results = []
    for cap in caps:
        if HAS_RICH:
            with console.status(f"Running {cap}..."):
                result = run_cap_evals(cap, mock=use_mock)
        else:
            print(f"Running {cap}...")
            result = run_cap_evals(cap, mock=use_mock)
        results.append(result)

    print_summary(results)


if __name__ == "__main__":
    main()
