"""MentorScript review agent for Cap-02."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any


def mentor_review_node(state: dict[str, Any]) -> dict[str, Any]:
    briefing = state.get("briefing")
    if briefing is None:
        return {**state, "status": "BLOCKED", "error_state": "missing briefing"}

    output_text = "\n".join(str(content) for content in state.get("output_files", {}).values())
    tests_passed = bool(state.get("test_results", {}).get("passed", False))
    trivial_tests = _has_trivial_tests(output_text)
    criteria_score_model = _schema_attr("CriteriaScore")
    criteria_status = _schema_attr("CriteriaStatus")
    scores = []
    for criterion in briefing.what_and_success.acceptance_criteria:
        if tests_passed and criterion.testable and not trivial_tests:
            status = criteria_status.PASS
            evidence = f"Passing test evidence for {criterion.id}: {criterion.test_command or 'test results'}"
        elif tests_passed:
            status = criteria_status.PARTIAL
            evidence = f"Partial evidence for {criterion.id}; test quality issue detected"
        else:
            status = criteria_status.FAIL
            evidence = f"No passing evidence found for {criterion.id}"
        scores.append(criteria_score_model(id=criterion.id, status=status, evidence=evidence))

    pass_rate = sum(score.status == criteria_status.PASS for score in scores) / len(scores) if scores else 0.0
    return {
        **state,
        "criteria_scores": scores,
        "acceptance_criteria_pass_rate": pass_rate,
        "test_quality_issues": ["trivial assertion detected"] if trivial_tests else [],
    }


def _has_trivial_tests(text: str) -> bool:
    return bool(re.search(r"assert\s+True\b|assert\s+1\s*==\s*1", text))


def _schema_attr(name: str) -> Any:
    schema_path = Path(__file__).parents[1] / "schemas" / "briefing_script.py"
    spec = importlib.util.spec_from_file_location("cap02_briefing_schema", schema_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load schema from {schema_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return getattr(module, name)
