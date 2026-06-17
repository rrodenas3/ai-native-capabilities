"""LangGraph state machine for Cap-01 Decision Intelligence."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NotRequired, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from core.governance import HumanApprovalGate
from core.orchestration.base_state import BaseAgentState
from core.schemas import AgentHop, AuditEvent, CapabilityID, Finding, RetrievalResult
from core.utils.settings import get_settings


class DecisionBriefState(BaseAgentState, total=False):
    """Cap-01 LangGraph state contract."""

    query: str
    user_role: str
    corpus_scope: list[str]
    sub_queries: list[str]
    retrieval_results: list[RetrievalResult]
    analysis_notes: str
    verification_flags: list[Any]
    executive_summary: str
    key_findings: list[Finding]
    uncertainty_flags: list[str]
    recommended_actions: list[str]
    overall_confidence: float
    brief: Any
    web_research_required: bool
    corpus_confidence: float
    evidence_strength: float
    citation_accuracy: float
    cost_tokens: int
    cost_telemetry: NotRequired[dict[str, Any]]


class Retriever(Protocol):
    def hybrid_search(
        self,
        query: str,
        k: int = 10,
        filters: dict[str, Any] | None = None,
        access_tier: str = "internal",
    ) -> list[RetrievalResult]: ...


def build_graph(
    retriever: Retriever,
    *,
    checkpointer: Any = None,
    require_human_review: bool = True,
    k_per_query: int = 10,
) -> CompiledStateGraph:
    """Build and compile the complete Cap-01 decision brief graph."""

    graph = StateGraph(DecisionBriefState)
    retrieval_node = build_retrieval_agent(retriever, k_per_query=k_per_query)
    human_gate = HumanApprovalGate(requires_approval=lambda _state: require_human_review)

    graph.add_node("supervisor", _with_transition_audit("supervisor", supervisor_node))
    graph.add_node("retrieval", _with_transition_audit("retrieval", retrieval_node))
    graph.add_node("analysis", _with_transition_audit("analysis", analysis_agent_node))
    graph.add_node("verification", _with_transition_audit("verification", verification_agent_node))
    graph.add_node("assembly", _with_transition_audit("assembly", brief_agent_node))
    graph.add_node("human_gate", _with_transition_audit("human_gate", human_gate))
    graph.add_node("cost_telemetry", cost_telemetry_node)

    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "retrieval")
    graph.add_edge("retrieval", "analysis")
    graph.add_edge("analysis", "verification")
    graph.add_edge("verification", "assembly")
    graph.add_edge("assembly", "human_gate")
    graph.add_edge("human_gate", "cost_telemetry")
    graph.add_edge("cost_telemetry", END)

    return graph.compile(checkpointer=checkpointer, name="cap-01-decision-brief")


def cost_telemetry_node(state: DecisionBriefState) -> dict[str, Any]:
    """Aggregate cost and token counters across all agent hops."""

    tokens = 0
    cost_usd = 0.0
    for hop in state.get("agent_hops", []):
        if isinstance(hop, AgentHop):
            tokens += hop.tokens_in + hop.tokens_out
            cost_usd += hop.cost_usd
        elif isinstance(hop, dict):
            tokens += int(hop.get("tokens_in", 0)) + int(hop.get("tokens_out", 0))
            cost_usd += float(hop.get("cost_usd", 0.0))

    return {
        "cost_tokens": tokens,
        "cost_telemetry": {
            "tokens": tokens,
            "cost_usd": round(cost_usd, 6),
            "hop_count": len(state.get("agent_hops", [])),
            "run_id": state.get("run_id"),
        },
    }


@contextmanager
def build_postgres_checkpointer(
    database_url: str | None = None,
    *,
    setup: bool = False,
) -> Iterator[Any]:
    """Create a PostgreSQL-backed LangGraph checkpointer."""

    from langgraph.checkpoint.postgres import PostgresSaver

    resolved_url = database_url or get_settings().DATABASE_URL
    if not resolved_url.startswith(("postgresql://", "postgres://")):
        raise ValueError("Invalid PostgreSQL connection string for LangGraph checkpointer")
    try:
        with PostgresSaver.from_conn_string(resolved_url) as checkpointer:
            if setup:
                checkpointer.setup()
            yield checkpointer
    except Exception as exc:
        raise RuntimeError("Failed to initialize PostgreSQL checkpointer") from exc


def initial_state(query: str, *, run_id: str, session_id: str, user_role: str = "executive") -> DecisionBriefState:
    """Create a minimal JSON-serialisable state for graph invocation."""

    return {
        "run_id": run_id,
        "session_id": session_id,
        "capability_id": CapabilityID.DECISION_INTELLIGENCE.value,
        "query": query,
        "user_role": user_role,
        "messages": [],
        "current_agent": "",
        "agent_hops": [],
        "audit_trail": [],
        "error_state": None,
        "human_approved": None,
        "cost_tokens": 0,
        "latency_ms": 0.0,
    }


def _with_transition_audit(name: str, node: Any):
    def wrapped(state: DecisionBriefState) -> dict[str, Any]:
        before = state.get("current_agent", "")
        if state.get("error_state"):
            audit_trail = list(state.get("audit_trail", []))
            audit_trail.append(
                AuditEvent(
                    capability=CapabilityID.DECISION_INTELLIGENCE,
                    run_id=str(state.get("run_id", "")),
                    session_id=str(state.get("session_id", "")),
                    event_type="graph.transition",
                    agent_name=name,
                    action="node_skipped",
                    payload={"from": before, "to": name, "reason": "error_state_present"},
                )
            )
            return {"audit_trail": audit_trail}

        try:
            update = node(state)
            audit_trail = list(update.get("audit_trail", state.get("audit_trail", [])))
            success = True
            payload: dict[str, Any] = {"from": before, "to": name}
        except Exception as exc:
            update = {
                "current_agent": name,
                "error_state": {
                    "node": name,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            }
            audit_trail = list(state.get("audit_trail", []))
            success = False
            payload = {
                "from": before,
                "to": name,
                "error_type": type(exc).__name__,
            }
        audit_trail.append(
            AuditEvent(
                capability=CapabilityID.DECISION_INTELLIGENCE,
                run_id=str(state.get("run_id", "")),
                session_id=str(state.get("session_id", "")),
                event_type="graph.transition",
                agent_name=name,
                action="node_completed" if success else "node_failed",
                payload=payload,
            )
        )
        return {**update, "audit_trail": audit_trail}

    return wrapped


def _load_attr(module_name: str, relative_path: str, attr: str) -> Any:
    existing = sys.modules.get(module_name)
    if existing is not None and hasattr(existing, attr):
        return getattr(existing, attr)

    module_path = Path(__file__).parent / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {attr} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return getattr(module, attr)


supervisor_node = _load_attr("cap01_supervisor", "supervisor.py", "supervisor_node")
build_retrieval_agent = _load_attr("cap01_retrieval_agent", "retrieval_agent.py", "build_retrieval_agent")
analysis_agent_node = _load_attr("cap01_analysis_agent", "analysis_agent.py", "analysis_agent_node")
verification_agent_node = _load_attr("cap01_verification_agent", "verification_agent.py", "verification_agent_node")
brief_agent_node = _load_attr("cap01_brief_agent", "brief_agent.py", "brief_agent_node")
