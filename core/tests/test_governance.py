from __future__ import annotations

import pytest

from core.governance import GATE_DEFINITIONS, GovernanceGateEngine, HumanApprovalGate
from core.governance.human_gate import requires_value_approval
from core.schemas.base import AuditEvent


def base_state(**overrides):
    state = {
        "run_id": "run-1",
        "session_id": "session-1",
        "capability_id": "cap-04",
        "messages": [],
        "current_agent": "replenishment",
        "agent_hops": [],
        "error_state": None,
        "human_approved": None,
        "audit_trail": [],
        "cost_tokens": 0,
        "latency_ms": 0.0,
        "value_usd": 6000.0,
    }
    state.update(overrides)
    return state


def test_all_five_gate_definitions_exist() -> None:
    assert list(GATE_DEFINITIONS) == [
        "gate_1_use_case",
        "gate_2_data",
        "gate_3_action",
        "gate_4_quality",
        "gate_5_scale",
    ]


def test_gate_engine_passes_complete_gate() -> None:
    result = GovernanceGateEngine().evaluate(
        "gate_1_use_case",
        {
            "high_frequency": True,
            "high_friction": True,
            "addressable_data": True,
            "clear_kpi": True,
        },
    )

    assert result.passed is True
    assert result.gate_number == 1


def test_gate_engine_holds_missing_criteria() -> None:
    result = GovernanceGateEngine().evaluate("gate_2_data", {"permissions_mapped": True})

    assert result.passed is False
    assert "Missing criteria" in str(result.notes)


def test_quality_gate_uses_eval_threshold() -> None:
    result = GovernanceGateEngine(eval_pass_threshold=0.9).evaluate(
        "gate_4_quality",
        {
            "eval_pass_rate": 0.89,
            "hallucination_within_budget": True,
            "latency_within_budget": True,
            "cost_within_budget": True,
        },
    )

    assert result.criteria_results["eval_pass_rate"] is False
    assert result.passed is False


def test_requires_value_approval_uses_configured_threshold(monkeypatch) -> None:
    monkeypatch.setenv("AUTONOMOUS_ACTION_THRESHOLD_USD", "5000")

    assert requires_value_approval(base_state(value_usd=5000.0)) is True
    assert requires_value_approval(base_state(value_usd=4999.0)) is False


def test_human_gate_uses_interrupt_and_logs_approval() -> None:
    calls = []

    def fake_interrupt(payload):
        calls.append(payload)
        return {"status": "approved", "approved_by": "ops-lead"}

    gate = HumanApprovalGate(interrupt_fn=fake_interrupt)

    result = gate(base_state())

    assert calls[0]["type"] == "human_approval_required"
    assert result["human_approved"] is True
    assert result["human_gate_status"] == "approved"
    assert isinstance(result["audit_trail"][0], AuditEvent)
    assert result["audit_trail"][0].event_type == "human_gate.approved"


def test_human_gate_rejects_when_decision_is_negative() -> None:
    gate = HumanApprovalGate(interrupt_fn=lambda payload: {"status": "rejected"})

    result = gate(base_state())

    assert result["human_approved"] is False
    assert result["human_gate_status"] == "rejected"


def test_human_gate_can_be_bypassed_only_in_ci_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("EVAL_MODE", "ci")
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("HUMAN_GATE_MOCK_APPROVED", "true")
    gate = HumanApprovalGate(interrupt_fn=lambda payload: pytest.fail("interrupt should be bypassed"))

    result = gate(base_state())

    assert result["human_approved"] is True
    assert result["audit_trail"][0].approved_by == "ci-mock"


def test_human_gate_does_not_bypass_without_mock_flag(monkeypatch) -> None:
    monkeypatch.setenv("EVAL_MODE", "ci")
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.delenv("HUMAN_GATE_MOCK_APPROVED", raising=False)
    gate = HumanApprovalGate(interrupt_fn=lambda payload: {"status": "approved"})

    result = gate(base_state())

    assert result["human_approved"] is True

