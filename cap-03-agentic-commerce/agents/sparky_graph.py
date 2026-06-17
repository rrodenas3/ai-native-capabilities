"""Sparky customer super-agent LangGraph."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cap03_loader import load_attr  # noqa: E402

classify_intent = load_attr("cap03_intent", "agents/intent_classifier.py", "classify_intent")
discovery_node = load_attr("cap03_discovery", "agents/discovery_agent.py", "discovery_node")
support_node = load_attr("cap03_support", "agents/support_agent.py", "support_node")
detect_sentiment = load_attr("cap03_sentiment", "tools/sentiment.py", "detect_sentiment")
escalation_node = load_attr("cap03_escalation", "agents/escalation_agent.py", "escalation_node")


class CommerceSessionState(TypedDict, total=False):
    session_id: str
    agent_type: str
    channel: str
    raw_message: str
    intent_class: str
    intent_confidence: float
    sub_intent: str | None
    customer_id: str | None
    order_history: list[dict[str, Any]]
    preferences: dict[str, Any]
    sentiment_score: float
    frustration_flag: bool
    search_query: str | None
    catalog_results: list[Any]
    recommendations: list[Any]
    basket: list[dict[str, Any]]
    margin_scores: dict[str, float]
    escalation_triggered: bool
    escalation_reason: str | None
    human_agent_id: str | None
    complexity_tier: str
    session_outcome: str | None
    resolution: Any
    agent_hops: list[dict[str, Any]]
    cost_tokens: int


def build_graph(*, checkpointer: Any = None) -> CompiledStateGraph:
    graph = StateGraph(CommerceSessionState)
    graph.add_node("sentiment", sentiment_node)
    graph.add_node("intent", intent_node)
    graph.add_node("discovery", discovery_node)
    graph.add_node("support", support_node)
    graph.add_node("escalation", escalation_node)
    graph.add_node("memory", memory_node)

    graph.add_edge(START, "sentiment")
    graph.add_edge("sentiment", "intent")
    graph.add_conditional_edges(
        "intent",
        _route,
        {"discovery": "discovery", "support": "support", "escalation": "escalation"},
    )
    graph.add_edge("discovery", "memory")
    graph.add_edge("support", "escalation")
    graph.add_edge("escalation", "memory")
    graph.add_edge("memory", END)
    return graph.compile(checkpointer=checkpointer, name="cap-03-sparky")


def initial_state(message: str, *, session_id: str, customer_id: str | None = None) -> CommerceSessionState:
    return {
        "session_id": session_id,
        "agent_type": "sparky",
        "channel": "web",
        "raw_message": message,
        "customer_id": customer_id,
        "order_history": [],
        "preferences": {},
        "basket": [],
        "agent_hops": [],
        "cost_tokens": 0,
    }


def sentiment_node(state: CommerceSessionState) -> dict[str, Any]:
    result = detect_sentiment(str(state.get("raw_message", "")))
    return {
        **state,
        "sentiment_score": result.sentiment_score,
        "frustration_flag": result.frustration_flag,
        "sentiment_triggers": result.triggers,
    }


def intent_node(state: CommerceSessionState) -> dict[str, Any]:
    result = classify_intent(str(state.get("raw_message", "")))
    return {
        **state,
        "intent_class": result.intent_class.value,
        "intent_confidence": result.intent_confidence,
        "sub_intent": result.sub_intent,
    }


def memory_node(state: CommerceSessionState) -> dict[str, Any]:
    store = state.get("session_store")
    if store is not None:
        store.store_session(
            str(state.get("session_id", "")),
            opt_in=bool(state.get("memory_opt_in", False)),
            customer_id=state.get("customer_id"),
            preferences=state.get("preferences", {}),
            order_history=state.get("order_history", []),
            session_outcome=state.get("session_outcome"),
        )
    return state


def _route(state: CommerceSessionState) -> str:
    if state.get("frustration_flag"):
        return "escalation"
    intent = state.get("intent_class")
    if intent in {"ESCALATION", "COMPLAINT"}:
        return "escalation"
    if intent in {"SUPPORT", "REORDER"}:
        return "support"
    return "discovery"
