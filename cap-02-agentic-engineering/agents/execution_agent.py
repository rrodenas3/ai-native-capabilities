"""Deterministic Cap-02 execution agent."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from core.harness.loop import ConsultationRequestPack


def execution_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    briefing = state.get("briefing")
    if briefing is None:
        return {**state, "status": "BLOCKED", "error_state": "missing briefing"}
    if str(state.get("git_branch", "feature/cap02")).lower() in {"main", "master"}:
        crp = _crp("TASK-branch", ["Checked current branch"], ["Current branch is protected"], "Create a feature branch before executing.")
        return {**state, "status": "CRP_PENDING", "crps_raised": [*state.get("crps_raised", []), crp]}

    files_changed = [f"generated/{briefing.briefing_id.lower()}.py"]
    tests_added = [f"tests/test_{briefing.briefing_id.lower().replace('-', '_')}.py"]
    output_files = {
        files_changed[0]: "def generated_value():\n    return 'sase-ready'\n",
        tests_added[0]: "def test_generated_value():\n    assert generated_value() == 'sase-ready'\n",
    }
    loop_script = {
        "plan": [task.description for task in briefing.implementation_tasks],
        "iterations": len(briefing.implementation_tasks),
        "acceptance_criteria": [criterion.id for criterion in briefing.what_and_success.acceptance_criteria],
    }
    return {
        **state,
        "status": "EXECUTED",
        "loop_script": loop_script,
        "files_changed": files_changed,
        "tests_added": tests_added,
        "output_files": output_files,
        "test_results": {"passed": True, "coverage_pct": float(state.get("coverage_pct", 0.86))},
    }


def _crp(task_id: str, tried: list[str], failed: list[str], proposed: str) -> ConsultationRequestPack:
    runtime_path = Path(__file__).parent / "loop_runtime.py"
    spec = importlib.util.spec_from_file_location("cap02_loop_runtime", runtime_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load loop runtime from {runtime_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.LoopRuntime().raise_crp(task_id, what_was_tried=tried, what_failed=failed, proposed_solution=proposed)
