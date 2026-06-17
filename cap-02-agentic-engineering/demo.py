"""Cap-02 mock SASE demo that produces a Merge-Readiness Pack."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run_demo() -> dict:
    schema = _load("schemas/briefing_script.py", "cap02_demo_schema")
    execution = _load("agents/execution_agent.py", "cap02_demo_execution")
    mentor = _load("agents/mentor_agent.py", "cap02_demo_mentor")
    security = _load("tools/security_gate.py", "cap02_demo_security")
    mrp = _load("agents/mrp_agent.py", "cap02_demo_mrp")
    briefing = schema.minimal_valid_briefing()
    state = execution.execution_agent_node({"briefing": briefing, "git_branch": "feature/cap02-demo"})
    state = mentor.mentor_review_node(state)
    state = security.security_gate_node(state)
    state = mrp.mrp_agent_node(state)
    pack = state.get("merge_readiness_pack")
    if pack is None:
        raise RuntimeError("State missing required key: merge_readiness_pack")
    return pack.model_dump(mode="json")


def _load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_report(pack: dict) -> dict:
    """Wrap MRP in canonical report envelope."""
    decision = pack.get("decision", "UNKNOWN")
    security = pack.get("security_clearance", {})
    score = pack.get("briefing_score", 0.0)
    return {
        "cap": "cap-02",
        "status": "pass" if decision == "APPROVE" else "fail",
        "score": score if isinstance(score, float) else 0.0,
        "metrics": {
            "briefing_score": score if isinstance(score, float) else 0.0,
            "security_cleared": 1.0 if security.get("cleared", False) else 0.0,
        },
        "blocking_failures": [] if decision == "APPROVE" else ["merge_blocked"],
        "merge_readiness_pack": pack,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cap-02 SASE merge readiness demo")
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write JSON report to FILE in the standard report envelope format",
    )
    args = parser.parse_args()

    pack = run_demo()

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            report = _build_report(pack)
            output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: could not write output to {args.output}: {exc}", file=sys.stderr)
            sys.exit(1)

    print(json.dumps(pack, indent=2))
