"""Human approval gate for high-value Cap-04 actions."""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt


def approval_gate_node(state: dict[str, Any]) -> dict[str, Any]:
    requires_approval = bool(state.get("human_approval_required"))
    high_value_pos = [po for po in state.get("po_drafts", []) if po.get("classification") == "HUMAN_APPROVAL"]
    if not requires_approval and not high_value_pos:
        return {**state, "human_approval_status": "not_required"}
    if state.get("human_approval_status") in {"approved", "modified"}:
        return state

    payload = {
        "type": "cap04_human_approval_required",
        "run_id": state.get("run_id"),
        "po_drafts": high_value_pos or state.get("po_drafts", []),
        "simulation_results": state.get("simulation_results", []),
        "aggregate_value_usd": sum(float(po.get("value_usd", 0.0)) for po in high_value_pos),
    }
    decision = interrupt(payload)
    status = str(decision.get("status", "rejected")) if isinstance(decision, dict) else "rejected"
    return {
        **state,
        "human_approval_status": status,
        "approver_id": decision.get("approver_id") if isinstance(decision, dict) else None,
        "human_modifications": decision.get("modifications", []) if isinstance(decision, dict) else [],
    }
