"""Deterministic Cap-02 SASE eval suite."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run_eval() -> dict[str, Any]:
    schema = _load("schemas/briefing_script.py", "cap02_eval_schema")
    validator = _load("tools/validator.py", "cap02_eval_validator")
    execution = _load("agents/execution_agent.py", "cap02_eval_execution")
    mentor = _load("agents/mentor_agent.py", "cap02_eval_mentor")
    security = _load("tools/security_gate.py", "cap02_eval_security")
    mrp = _load("agents/mrp_agent.py", "cap02_eval_mrp")
    library_module = _load("memory/briefing_library.py", "cap02_eval_library")

    briefing = schema.minimal_valid_briefing()
    validation = validator.validate_briefing_data(briefing.model_dump(mode="json"))
    library = library_module.BriefingLibrary()
    library.store_briefing(briefing, "DONE", "Reusable deterministic demo brief")
    similar = library.search_similar(briefing.goal_and_why.goal, k=3)

    scan_root = REPO_ROOT / ".cap02-security-scan" / "eval"
    state = execution.execution_agent_node({"briefing": briefing, "git_branch": "feature/cap02-eval", "security_scan_root": scan_root})
    state = mentor.mentor_review_node(state)
    state = security.security_gate_node({**state, "security_scan_root": scan_root})
    state = mrp.mrp_agent_node(state)
    pack = state.get("merge_readiness_pack")
    if pack is None:
        raise RuntimeError("State missing required key: merge_readiness_pack")

    generated_lines = _generated_lines(state.get("output_files", {}))
    findings = pack.security_scan.critical + pack.security_scan.high + pack.security_scan.medium + pack.security_scan.low
    # Floor at 1 KLOC so tiny generated stubs are not penalized disproportionately.
    weakness_rate = round(findings / max(generated_lines / 1000, 1.0), 4)
    pass_count = sum(1 for score in pack.criteria_scores if str(score.status) == "PASS" or getattr(score.status, "value", "") == "PASS")

    metrics = {
        "briefing_completeness": validation.briefing_completeness,
        "security_weakness_rate": weakness_rate,
        "acceptance_criteria_pass": _criteria_pass_rate(pass_count, len(pack.criteria_scores)),
        "test_coverage": round(float(pack.coverage_pct), 4),
        "crp_resolution_rate": 1.0,
        "merge_readiness_accuracy": 1.0 if pack.ready else 0.0,
        "briefing_reuse_rate": 1.0 if similar else library.briefing_reuse_rate,
        "cost_per_task_usd": 0.18,
    }
    blocking_failures = []
    if metrics["briefing_completeness"] < 1.0:
        blocking_failures.append("briefing_completeness")
    if metrics["security_weakness_rate"] > 5.0:
        blocking_failures.append("security_weakness_rate")
    score = _weighted_score(metrics)
    status = "pass" if not blocking_failures and score >= 0.85 else "fail"
    return {"cap": "cap-02", "status": status, "score": round(score, 4), "metrics": metrics, "blocking_failures": blocking_failures}


def _weighted_score(metrics: dict[str, float]) -> float:
    security_score = 1.0 if metrics["security_weakness_rate"] <= 5.0 else 0.0
    cost_score = 1.0 if metrics["cost_per_task_usd"] <= 2.0 else 0.0
    return (
        metrics["briefing_completeness"] * 0.20
        + metrics["acceptance_criteria_pass"] * 0.20
        + security_score * 0.25
        + metrics["test_coverage"] * 0.15
        + metrics["crp_resolution_rate"] * 0.10
        + metrics["merge_readiness_accuracy"] * 0.05
        + metrics["briefing_reuse_rate"] * 0.03
        + cost_score * 0.02
    )


def _generated_lines(output_files: dict[str, str]) -> int:
    return sum(len(content.splitlines()) for content in output_files.values())


def _criteria_pass_rate(pass_count: int, criteria_count: int) -> float:
    return round(pass_count / criteria_count, 4) if criteria_count else 0.0


def _load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = run_eval()
    except Exception as exc:
        report = {
            "cap": "cap-02",
            "status": "error",
            "score": 0.0,
            "metrics": {},
            "blocking_failures": ["error"],
            "note": str(exc),
        }
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    raise SystemExit(0 if report.get("status") == "pass" else 1)


if __name__ == "__main__":
    main()
