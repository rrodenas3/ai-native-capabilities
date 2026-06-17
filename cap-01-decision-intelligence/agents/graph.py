"""LangGraph state machine for Cap-01 Decision Intelligence."""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Any, NotRequired, Protocol

from langgraph.errors import GraphInterrupt
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from core.governance import HumanApprovalGate
from core.observability.cost import BudgetAlertHandler, CostTelemetry
from core.observability.telemetry import trace_agent_hop
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
    brief_stored: bool
    brief_memory_event_id: str
    web_research_required: bool
    corpus_confidence: float
    evidence_strength: float
    citation_accuracy: float
    human_gate_status: str
    human_override_rate: float
    cost_tokens: int
    cost_tokens_in: int
    cost_tokens_out: int
    cost_usd_total: float
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
    episodic_memory: Any = None,
    require_human_review: bool = True,
    k_per_query: int = 10,
    budget_alert_handler: BudgetAlertHandler | None = None,
    cost_telemetry: CostTelemetry | None = None,
) -> CompiledStateGraph:
    """Build and compile the complete Cap-01 decision brief graph."""

    graph = StateGraph(DecisionBriefState)
    retrieval_node = build_retrieval_agent(retriever, k_per_query=k_per_query)
    human_gate = HumanApprovalGate(requires_approval=lambda _state: require_human_review)
    telemetry = cost_telemetry or CostTelemetry(budget_alert_handler=budget_alert_handler)

    graph.add_node("supervisor", _with_transition_audit("supervisor", supervisor_node, telemetry))
    graph.add_node("retrieval", _with_transition_audit("retrieval", retrieval_node, telemetry))
    graph.add_node("analysis", _with_transition_audit("analysis", analysis_agent_node, telemetry))
    graph.add_node("verification", _with_transition_audit("verification", verification_agent_node, telemetry))
    graph.add_node("assembly", _with_transition_audit("assembly", brief_agent_node, telemetry))
    graph.add_node("human_gate", _with_transition_audit("human_gate", human_gate, telemetry))
    graph.add_node("episodic_memory", _with_transition_audit("episodic_memory", _memory_store_node(episodic_memory), telemetry))
    graph.add_node("cost_telemetry", cost_telemetry_node)

    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "retrieval")
    graph.add_edge("retrieval", "analysis")
    graph.add_edge("analysis", "verification")
    graph.add_edge("verification", "assembly")
    graph.add_edge("assembly", "human_gate")
    graph.add_edge("human_gate", "episodic_memory")
    graph.add_edge("episodic_memory", "cost_telemetry")
    graph.add_edge("cost_telemetry", END)

    return graph.compile(checkpointer=checkpointer, name="cap-01-decision-brief")


def cost_telemetry_node(state: DecisionBriefState) -> dict[str, Any]:
    """Aggregate cost and token counters across all agent hops."""

    tokens_in = 0
    tokens_out = 0
    cost_usd = 0.0
    for hop in state.get("agent_hops", []):
        if isinstance(hop, AgentHop):
            tokens_in += hop.tokens_in
            tokens_out += hop.tokens_out
            cost_usd += hop.cost_usd
        elif isinstance(hop, dict):
            tokens_in += int(hop.get("tokens_in", 0))
            tokens_out += int(hop.get("tokens_out", 0))
            cost_usd += float(hop.get("cost_usd", 0.0))

    total_tokens = tokens_in + tokens_out
    cost_usd = round(cost_usd, 6)
    return {
        "cost_tokens": total_tokens,
        "cost_tokens_in": tokens_in,
        "cost_tokens_out": tokens_out,
        "cost_usd_total": cost_usd,
        "human_override_rate": _human_override_rate(state),
        "cost_telemetry": {
            "tokens": total_tokens,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "cost_per_brief_usd": cost_usd,
            "hop_count": len(state.get("agent_hops", [])),
            "human_override_rate": _human_override_rate(state),
            "run_id": state.get("run_id"),
        },
    }


def _memory_store_node(episodic_memory: Any):
    def store_completed_brief(state: DecisionBriefState) -> dict[str, Any]:
        if episodic_memory is None or state.get("human_approved") is not True or state.get("brief") is None:
            return {"brief_stored": False}

        event_id = episodic_memory.store_brief(
            state["brief"],
            str(state.get("session_id", "")),
            str(state.get("run_id", "")),
            query=str(state.get("query", "")),
            cost_usd=float(state.get("cost_telemetry", {}).get("cost_usd", 0.0))
            if isinstance(state.get("cost_telemetry"), dict)
            else None,
            latency_ms=float(state.get("latency_ms", 0.0)),
            metadata={"human_gate_status": state.get("human_gate_status")},
        )
        return {"brief_stored": True, "brief_memory_event_id": event_id}

    return store_completed_brief


def _human_override_rate(state: DecisionBriefState) -> float:
    status = state.get("human_gate_status")
    if status in {"rejected", "modified"}:
        return 1.0
    if status == "approved":
        return 0.0
    return 0.0


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
        "cost_tokens_in": 0,
        "cost_tokens_out": 0,
        "cost_usd_total": 0.0,
        "latency_ms": 0.0,
    }


def _with_transition_audit(name: str, node: Any, telemetry: CostTelemetry | None = None):
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
            started = perf_counter()
            update = node(state)
            latency_ms = (perf_counter() - started) * 1000
            update = _record_new_hops(state, update, latency_ms, telemetry)
            audit_trail = list(update.get("audit_trail", state.get("audit_trail", [])))
            success = True
            payload: dict[str, Any] = {"from": before, "to": name}
        except GraphInterrupt:
            raise
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


def _record_new_hops(
    before_state: DecisionBriefState,
    update: dict[str, Any],
    latency_ms: float,
    telemetry: CostTelemetry | None,
) -> dict[str, Any]:
    before_hops = list(before_state.get("agent_hops", []))
    after_hops = list(update.get("agent_hops", before_hops))
    if len(after_hops) <= len(before_hops):
        return update

    tokens_in = _estimate_tokens(before_state)
    tokens_out = max(_estimate_tokens(update) - tokens_in, _estimate_tokens(_changed_fields(before_state, update)))
    tokens_in = max(tokens_in, 1)
    tokens_out = max(tokens_out, 1)
    run_id = str(update.get("run_id") or before_state.get("run_id") or "")

    enriched_hops = [*_normalise_hops(after_hops[: len(before_hops)])]
    for hop in _normalise_hops(after_hops[len(before_hops) :]):
        event = telemetry.record_llm_call(
            hop.model,
            tokens_in,
            tokens_out,
            latency_ms,
            hop.agent_name,
            run_id,
        ) if telemetry is not None else None
        enriched = hop.model_copy(
            update={
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": round(latency_ms, 3),
                "cost_usd": event.cost_usd if event is not None else hop.cost_usd,
            }
        )
        with trace_agent_hop(enriched):
            pass
        enriched_hops.append(enriched)
    return {**update, "agent_hops": enriched_hops}


def _normalise_hops(hops: list[Any]) -> list[AgentHop]:
    normalised: list[AgentHop] = []
    for hop in hops:
        if isinstance(hop, AgentHop):
            normalised.append(hop)
        elif isinstance(hop, dict):
            normalised.append(AgentHop(**hop))
    return normalised


def _estimate_tokens(value: Any) -> int:
    text = json.dumps(_jsonable(value), sort_keys=True, default=str)
    return max(1, len(text) // 12)


def _changed_fields(before_state: DecisionBriefState, update: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in update.items()
        if key not in before_state or before_state.get(key) != value
    }


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_jsonable(inner) for inner in value]
    if isinstance(value, tuple):
        return [_jsonable(inner) for inner in value]
    return value


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
