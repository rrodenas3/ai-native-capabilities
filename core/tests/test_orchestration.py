from __future__ import annotations

import pytest
from langgraph.graph.state import CompiledStateGraph

from core.orchestration import BaseAgentState, BaseCapabilityGraph
from core.schemas.base import AgentHop, AgentHopType


class DecisionBriefState(BaseAgentState, total=False):
    query: str


def base_state() -> DecisionBriefState:
    return {
        "run_id": "run-1",
        "session_id": "session-1",
        "capability_id": "cap-01",
        "messages": [],
        "current_agent": "supervisor",
        "agent_hops": [],
        "error_state": None,
        "human_approved": None,
        "audit_trail": [],
        "cost_tokens": 0,
        "latency_ms": 0.0,
        "query": "What changed?",
    }


def test_capability_state_can_extend_base_state() -> None:
    state = base_state()

    assert state["capability_id"] == "cap-01"
    assert state["query"] == "What changed?"


def test_build_returns_compiled_state_graph() -> None:
    graph = BaseCapabilityGraph("cap-01", DecisionBriefState)

    compiled = graph.build()

    assert isinstance(compiled, CompiledStateGraph)


def test_custom_node_compiles_and_updates_state() -> None:
    graph = BaseCapabilityGraph("cap-01", DecisionBriefState)
    graph.add_node("supervisor", lambda state: {"current_agent": "retrieval"}, terminal=True)

    result = graph.build().invoke(base_state())

    assert result["current_agent"] == "retrieval"


def test_human_gate_skips_interrupt_when_threshold_is_false() -> None:
    graph = BaseCapabilityGraph("cap-01", DecisionBriefState)
    graph.add_node("supervisor", lambda state: {"current_agent": "supervisor"}, terminal=True)
    gate_name = graph.add_human_gate("supervisor", lambda state: False)

    result = graph.build().invoke(base_state())

    assert gate_name == "supervisor_human_gate"
    assert result["human_approved"] is None


def test_human_gate_can_use_existing_approval() -> None:
    graph = BaseCapabilityGraph("cap-01", DecisionBriefState)
    graph.add_node("supervisor", lambda state: {"current_agent": "supervisor"}, terminal=True)
    graph.add_human_gate("supervisor", lambda state: True)
    state = base_state()
    state["human_approved"] = True

    result = graph.build().invoke(state)

    assert result["human_approved"] is True


def test_eval_node_records_metrics() -> None:
    graph = BaseCapabilityGraph("cap-01", DecisionBriefState)
    graph.add_node("supervisor", lambda state: {"current_agent": "supervisor"}, terminal=True)
    graph.add_eval_node(["task_success_rate", "hallucination_rate"])

    result = graph.build().invoke(base_state())

    assert result["eval_metrics"] == ["task_success_rate", "hallucination_rate"]


def test_cost_telemetry_aggregates_agent_hops() -> None:
    graph = BaseCapabilityGraph("cap-01", DecisionBriefState)
    graph.add_node("supervisor", lambda state: {"current_agent": "supervisor"}, terminal=True)
    graph.add_cost_telemetry()
    state = base_state()
    state["agent_hops"] = [
        AgentHop(
            agent_name="supervisor",
            hop_type=AgentHopType.SUPERVISOR,
            model="test-model",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.001,
        )
    ]

    result = graph.build().invoke(state)

    assert result["cost_tokens"] == 30
    assert result["cost_telemetry"]["cost_usd"] == 0.001
    assert result["cost_telemetry"]["run_id"] == "run-1"


def test_cannot_mutate_after_build() -> None:
    graph = BaseCapabilityGraph("cap-01", DecisionBriefState)
    graph.build()

    with pytest.raises(RuntimeError):
        graph.add_node("late", lambda state: state)
