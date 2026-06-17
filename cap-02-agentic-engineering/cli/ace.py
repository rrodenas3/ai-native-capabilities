"""Agent Command Environment CLI for Cap-02."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app = typer.Typer(help="Cap-02 Agent Command Environment")
crp_app = typer.Typer(help="Consultation Request Pack commands")
app.add_typer(crp_app, name="crp")
console = Console()
BRIEFING_OUTPUT_OPTION = typer.Option(Path("briefing.json"), "--output", "-o")
CRP_QUEUE_OPTION = typer.Option(Path("reports/cap02-crps.json"), "--queue")
CRP_RESPONSE_OPTION = typer.Option(..., "--response")


@app.command("new")
def new(output: Path = BRIEFING_OUTPUT_OPTION) -> None:
    """Create a new BriefingScript interactively."""

    goal = typer.prompt("Goal")
    why = typer.prompt("Why")
    business_value = typer.prompt("Business value")
    scope = typer.prompt("Scope")
    criterion = typer.prompt("Acceptance criterion")
    task = typer.prompt("Implementation task")
    instructions = typer.prompt("Codex instructions", default="Work on a branch, run tests, and raise CRP when blocked.")
    data = _briefing_data(goal, why, business_value, scope, criterion, task, instructions)
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    console.print(f"Wrote {output}")


@app.command("run")
def run(spec: Path) -> None:
    """Validate and submit a BriefingScript to the deterministic execution path."""

    validator = _load("tools/validator.py", "cap02_ace_validator")
    result = validator.validate_briefing(spec)
    if not result.valid:
        console.print("[red]BriefingScript invalid[/red]")
        console.print(result.model_dump_json(indent=2, exclude={"briefing"}))
        raise typer.Exit(1)
    demo = _load("demo.py", "cap02_ace_demo")
    pack = demo.run_demo()
    _print_mrp(pack)


@app.command("review")
def review(mrp: Path, decision: str = typer.Option("approve", "--decision")) -> None:
    """Review a Merge-Readiness Pack and approve or reject it."""

    pack = json.loads(mrp.read_text(encoding="utf-8"))
    _print_mrp(pack)
    if decision.lower() not in {"approve", "reject", "changes"}:
        raise typer.BadParameter("decision must be approve, reject, or changes")
    console.print(f"Decision: {decision.upper()}")


@crp_app.command("list")
def crp_list(queue: Path = CRP_QUEUE_OPTION) -> None:
    """List pending Consultation Requests."""

    crps = _read_json_list(queue)
    pending = [item for item in crps if item.get("status", "PENDING") == "PENDING"]
    table = Table(title="Pending CRPs")
    table.add_column("ID")
    table.add_column("Task")
    table.add_column("Proposed solution")
    for item in pending:
        table.add_row(str(item.get("id", "")), str(item.get("task_id", "")), str(item.get("proposed_solution", "")))
    console.print(table)


@crp_app.command("resolve")
def crp_resolve(crp_id: str, response: str = CRP_RESPONSE_OPTION, queue: Path = CRP_QUEUE_OPTION) -> None:
    """Resolve a Consultation Request."""

    crps = _read_json_list(queue)
    resolved = False
    for item in crps:
        if str(item.get("id")) == crp_id:
            item["status"] = "RESOLVED"
            item["response"] = response
            item["resolved_at"] = datetime.now(UTC).isoformat()
            resolved = True
    if not resolved:
        raise typer.BadParameter(f"CRP not found: {crp_id}")
    queue.parent.mkdir(parents=True, exist_ok=True)
    queue.write_text(json.dumps(crps, indent=2), encoding="utf-8")
    console.print(f"Resolved {crp_id}")


def _print_mrp(pack: dict[str, Any]) -> None:
    scan = pack.get("security_scan", {})
    summary = Table(title=f"Merge-Readiness Pack {pack.get('pack_id', '')}")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("Briefing", str(pack.get("briefing_id", "")))
    summary.add_row("Ready", str(pack.get("ready", False)))
    summary.add_row("Coverage", str(pack.get("coverage_pct", "")))
    summary.add_row("Files changed", ", ".join(pack.get("files_changed", [])))
    summary.add_row("Tests added", ", ".join(pack.get("tests_added", [])))
    summary.add_row("Security", f"critical={scan.get('critical', 0)} high={scan.get('high', 0)} medium={scan.get('medium', 0)} low={scan.get('low', 0)}")
    console.print(summary)
    criteria = Table(title="Acceptance Criteria")
    criteria.add_column("ID")
    criteria.add_column("Status")
    criteria.add_column("Evidence")
    for score in pack.get("criteria_scores", []):
        criteria.add_row(str(score.get("id", "")), str(score.get("status", "")), str(score.get("evidence", "")))
    console.print(criteria)


def _briefing_data(goal: str, why: str, business_value: str, scope: str, criterion: str, task: str, instructions: str) -> dict[str, Any]:
    return {
        "briefing_id": f"BRIEF-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "version": 1,
        "status": "APPROVED",
        "author": "agent-coach",
        "agent": "codex",
        "created_at": datetime.now(UTC).isoformat(),
        "goal_and_why": {"goal": goal, "why": why, "business_value": business_value},
        "what_and_success": {"scope": scope, "acceptance_criteria": [{"id": "AC-01", "description": criterion, "testable": True, "test_command": "pytest"}], "invariants": [], "anti_goals": []},
        "all_needed_context": {"architecture_refs": [], "relevant_files": [], "patterns_to_follow": [], "constraints": ["Do not commit directly to main."]},
        "implementation_tasks": [{"id": "TASK-01", "description": task, "depends_on": [], "estimated_complexity": "S"}],
        "failure_modes": [],
        "codex_instructions": instructions,
    }


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise typer.BadParameter("CRP queue must contain a JSON list")
    return payload


def _load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    app()
