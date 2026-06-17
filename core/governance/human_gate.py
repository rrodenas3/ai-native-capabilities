"""Human approval gate built on LangGraph interrupt()."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from langgraph.types import interrupt

from core.orchestration.base_state import BaseAgentState
from core.schemas.base import AuditEvent, CapabilityID, HumanGateStatus

InterruptFn = Callable[[dict[str, Any]], Any]
ApprovalPredicate = Callable[[BaseAgentState], bool]


def autonomous_action_threshold_usd() -> float:
    return float(os.getenv("AUTONOMOUS_ACTION_THRESHOLD_USD", "5000"))


def requires_value_approval(
    state: BaseAgentState,
    *,
    value_key: str = "value_usd",
    threshold_usd: float | None = None,
) -> bool:
    threshold = threshold_usd if threshold_usd is not None else autonomous_action_threshold_usd()
    value = float(state.get(value_key, 0.0))  # type: ignore[arg-type]
    return value >= threshold


class HumanApprovalGate:
    """Callable node that halts via LangGraph interrupt when approval is required."""

    def __init__(
        self,
        requires_approval: ApprovalPredicate = requires_value_approval,
        *,
        interrupt_fn: InterruptFn = interrupt,
    ) -> None:
        self.requires_approval = requires_approval
        self.interrupt_fn = interrupt_fn

    def __call__(self, state: BaseAgentState) -> dict[str, Any]:
        if not self.requires_approval(state):
            return {"human_approved": state.get("human_approved")}

        if _ci_mock_bypass_enabled():
            return self._decision_update(state, {"status": "approved", "approved_by": "ci-mock"})

        if state.get("human_approved") is True:
            return {"human_approved": True}

        decision = self.interrupt_fn(
            {
                "type": "human_approval_required",
                "run_id": state.get("run_id"),
                "session_id": state.get("session_id"),
                "capability_id": state.get("capability_id"),
                "value_usd": state.get("value_usd", 0.0),  # type: ignore[typeddict-item]
            }
        )
        return self._decision_update(state, _normalise_decision(decision))

    def _decision_update(self, state: BaseAgentState, decision: dict[str, Any]) -> dict[str, Any]:
        status = HumanGateStatus(decision.get("status", "rejected"))
        approved = status in (HumanGateStatus.APPROVED, HumanGateStatus.MODIFIED)
        audit_event = AuditEvent(
            capability=CapabilityID(str(state.get("capability_id", "cap-01"))),
            run_id=str(state.get("run_id")),
            session_id=str(state.get("session_id")),
            event_type=f"human_gate.{status.value}",
            agent_name=str(state.get("current_agent", "human_gate")),
            action="human_approval",
            payload=decision,
            decision=status.value,
            approved_by=decision.get("approved_by"),
        )
        audit_trail = list(state.get("audit_trail", []))
        audit_trail.append(audit_event)
        return {
            "human_approved": approved,
            "human_gate_status": status.value,
            "audit_trail": audit_trail,
        }


def _normalise_decision(decision: Any) -> dict[str, Any]:
    if isinstance(decision, dict):
        if "status" in decision:
            return decision
        if "approved" in decision:
            return {"status": "approved" if decision["approved"] else "rejected", **decision}
    if decision is True:
        return {"status": "approved"}
    return {"status": "rejected", "raw_decision": decision}


def _ci_mock_bypass_enabled() -> bool:
    return (
        os.getenv("EVAL_MODE") == "ci"
        and os.getenv("LLM_MODE") == "mock"
        and os.getenv("HUMAN_GATE_MOCK_APPROVED") == "true"
    )

