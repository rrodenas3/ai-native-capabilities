"""Merge-Readiness Pack assembly agent."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def mrp_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    briefing = state.get("briefing")
    security_scan = state.get("security_scan")
    if briefing is None or security_scan is None:
        return {**state, "status": "BLOCKED", "error_state": "missing briefing or security scan"}
    merge_readiness_pack_model = _schema_attr("MergeReadinessPack")
    scan = _dump(security_scan)
    ready = int(scan.get("critical", 0)) == 0
    pack = merge_readiness_pack_model(
        briefing_id=briefing.briefing_id,
        pack_id=f"MRP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        agent=briefing.agent,
        files_changed=list(state.get("files_changed", [])),
        tests_added=list(state.get("tests_added", [])),
        coverage_pct=float(state.get("test_results", {}).get("coverage_pct", 0.0)),
        security_scan=scan,
        criteria_scores=[_dump(score) for score in state.get("criteria_scores", [])],
        crps_raised=[_dump(crp) for crp in state.get("crps_raised", [])],
        crps_resolved=[_dump(crp) for crp in state.get("crps_resolved", [])],
        agent_notes=_notes(state),
        ready=ready,
    )
    return {**state, "merge_readiness_pack": pack, "human_review_artifact": pack, "status": "MRP_READY" if ready else "BLOCKED"}


def _notes(state: dict[str, Any]) -> str:
    return (
        f"Built {len(state.get('files_changed', []))} file(s), added {len(state.get('tests_added', []))} test file(s), "
        f"and scored {len(state.get('criteria_scores', []))} acceptance criterion/criteria. "
        "Reviewer should inspect any CRPs and security warnings before approval."
    )


def _dump(value: Any) -> Any:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def _schema_attr(name: str) -> Any:
    schema_path = Path(__file__).parents[1] / "schemas" / "briefing_script.py"
    spec = importlib.util.spec_from_file_location("cap02_briefing_schema", schema_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load schema from {schema_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return getattr(module, name)
