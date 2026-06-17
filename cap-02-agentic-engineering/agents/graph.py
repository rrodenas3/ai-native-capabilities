"""LangGraph state machine for Cap-02 SASE."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Protocol, TypedDict

from langgraph.errors import GraphInterrupt
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from core.governance import HumanApprovalGate
from core.schemas import CapabilityID


class SASEState(TypedDict, total=False):
    run_id: str
    session_id: str
    capability_id: str
    briefing_path: str
    briefing_data: dict[str, Any]
    briefing: Any
    validation_result: Any
    similar_briefings: list[Any]
    loop_script: dict[str, Any]
    files_changed: list[str]
    tests_added: list[str]
    output_files: dict[str, str]
    test_results: dict[str, Any]
    criteria_scores: list[Any]
    security_scan: Any
    merge_readiness_pack: Any
    human_review_artifact: Any
    human_approved: bool | None
    human_gate_status: str
    crps_raised: list[Any]
    crps_resolved: list[Any]
    status: str
    error_state: Any
    git_branch: str


class BriefingLibraryProtocol(Protocol):
    def search_similar(self, query: str, k: int = 3) -> list[Any]: ...


def build_graph(*, briefing_library: BriefingLibraryProtocol | None = None, checkpointer: Any = None) -> CompiledStateGraph:
    graph = StateGraph(SASEState)
    human_gate = HumanApprovalGate(requires_approval=lambda _state: True)

    graph.add_node("validate_briefing", validate_briefing_node)
    graph.add_node("search_library", search_library_node(briefing_library))
    graph.add_node("execute", execution_agent_node)
    graph.add_node("crp_queue", crp_queue_node)
    graph.add_node("mentor_review", mentor_review_node)
    graph.add_node("security_gate", security_gate_node)
    graph.add_node("assemble_mrp", mrp_agent_node)
    graph.add_node("human_review", human_gate)

    graph.add_edge(START, "validate_briefing")
    graph.add_conditional_edges(
        "validate_briefing",
        lambda state: "search_library" if state.get("status") == "VALID" else END,
        {"search_library": "search_library", END: END},
    )
    graph.add_edge("search_library", "execute")
    graph.add_conditional_edges(
        "execute",
        lambda state: "crp_queue" if state.get("status") == "CRP_PENDING" else "mentor_review",
        {"crp_queue": "crp_queue", "mentor_review": "mentor_review"},
    )
    graph.add_edge("crp_queue", "execute")
    graph.add_edge("mentor_review", "security_gate")
    graph.add_conditional_edges(
        "security_gate",
        lambda state: END if state.get("status") == "BLOCKED" else "assemble_mrp",
        {END: END, "assemble_mrp": "assemble_mrp"},
    )
    graph.add_conditional_edges(
        "assemble_mrp",
        lambda state: END if state.get("status") == "BLOCKED" else "human_review",
        {END: END, "human_review": "human_review"},
    )
    graph.add_edge("human_review", END)
    return graph.compile(checkpointer=checkpointer, name="cap-02-sase")


def initial_state(*, run_id: str, session_id: str, briefing_data: dict[str, Any] | None = None) -> SASEState:
    return {
        "run_id": run_id,
        "session_id": session_id,
        "capability_id": CapabilityID.AGENTIC_ENGINEERING.value,
        "briefing_data": briefing_data or {},
        "human_approved": None,
        "crps_raised": [],
        "crps_resolved": [],
        "git_branch": "feature/cap02",
    }


def validate_briefing_node(state: SASEState) -> dict[str, Any]:
    if state.get("briefing_path"):
        result = validate_briefing(state["briefing_path"])
    else:
        result = validate_briefing_data(dict(state.get("briefing_data", {})))
    if not result.valid:
        return {**state, "validation_result": result, "status": "INVALID_BRIEFING", "error_state": result.errors}
    return {**state, "validation_result": result, "briefing": result.briefing, "status": "VALID"}


def search_library_node(briefing_library: BriefingLibraryProtocol | None):
    def search(state: SASEState) -> dict[str, Any]:
        briefing = state.get("briefing")
        if briefing_library is None or briefing is None:
            return {**state, "similar_briefings": []}
        return {
            **state,
            "similar_briefings": briefing_library.search_similar(str(briefing.goal_and_why.goal), k=3),
        }

    return search


def crp_queue_node(state: SASEState) -> dict[str, Any]:
    try:
        resolution = interrupt(
            {
                "type": "consultation_request",
                "run_id": state.get("run_id"),
                "crps": [_dump(crp) for crp in state.get("crps_raised", [])],
            }
        )
    except GraphInterrupt:
        raise
    resolved = [*state.get("crps_resolved", []), resolution]
    return {**state, "crps_resolved": resolved, "status": "CRP_RESOLVED", "git_branch": "feature/cap02"}


def _dump(value: Any) -> Any:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def _load_attr(module_name: str, relative_path: str, attr: str) -> Any:
    existing = sys.modules.get(module_name)
    if existing is not None and hasattr(existing, attr):
        return getattr(existing, attr)

    module_path = Path(__file__).parent / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {attr} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    if spec.name not in sys.modules:
        sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return getattr(module, attr)


validate_briefing = _load_attr("cap02_validator", "../tools/validator.py", "validate_briefing")
validate_briefing_data = _load_attr("cap02_validator", "../tools/validator.py", "validate_briefing_data")
execution_agent_node = _load_attr("cap02_execution_agent", "execution_agent.py", "execution_agent_node")
mentor_review_node = _load_attr("cap02_mentor_agent", "mentor_agent.py", "mentor_review_node")
security_gate_node = _load_attr("cap02_security_gate", "../tools/security_gate.py", "security_gate_node")
mrp_agent_node = _load_attr("cap02_mrp_agent", "mrp_agent.py", "mrp_agent_node")
