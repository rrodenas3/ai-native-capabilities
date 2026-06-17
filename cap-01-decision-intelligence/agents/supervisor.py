"""Supervisor agent for Cap-01 Decision Intelligence."""

from __future__ import annotations

import re
from typing import Any

from core.schemas import AgentHop, AgentHopType, AuditEvent, CapabilityID
from core.utils.settings import get_settings

WEB_CONFIDENCE_THRESHOLD = 0.3


def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    """Decompose a strategic query and route retrieval work."""

    query = str(state.get("query", "")).strip()
    settings = get_settings()
    sub_queries = decompose_query(query)
    corpus_scope = determine_corpus_scope(query, state.get("corpus_scope"))
    corpus_confidence = float(state.get("corpus_confidence", estimate_corpus_confidence(query)))
    web_research_required = corpus_confidence < WEB_CONFIDENCE_THRESHOLD

    hop = AgentHop(
        agent_name="supervisor",
        hop_type=AgentHopType.SUPERVISOR,
        model=settings.LLM_DEFAULT,
        confidence=corpus_confidence,
    )
    audit_event = AuditEvent(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        run_id=str(state.get("run_id", "")),
        session_id=str(state.get("session_id", "")),
        event_type="supervisor.routed",
        agent_name="supervisor",
        action="decompose_and_route",
        payload={
            "query": query,
            "sub_queries": sub_queries,
            "corpus_scope": corpus_scope,
            "corpus_confidence": corpus_confidence,
            "web_research_required": web_research_required,
        },
    )

    return {
        **state,
        "current_agent": "supervisor",
        "sub_queries": sub_queries,
        "corpus_scope": corpus_scope,
        "corpus_confidence": corpus_confidence,
        "web_research_required": web_research_required,
        "next_agents": ["retrieval", "web_research"] if web_research_required else ["retrieval"],
        "agent_hops": [*state.get("agent_hops", []), hop],
        "audit_trail": [*state.get("audit_trail", []), audit_event],
    }


def decompose_query(query: str) -> list[str]:
    cleaned = query.strip().rstrip("?")
    if not cleaned:
        return []

    parts = re.split(r"\s+(?:and|;|, plus|, and)\s+", cleaned, flags=re.IGNORECASE)
    sub_queries = [_normalise_subquery(part) for part in parts if part.strip()]
    if len(sub_queries) == 1 and any(word in cleaned.lower() for word in ("risks", "opportunities", "competitors")):
        sub_queries = _expand_strategic_query(cleaned)
    return _dedupe(sub_queries)


def determine_corpus_scope(query: str, existing_scope: Any = None) -> list[str]:
    if existing_scope is not None:
        return list(existing_scope)
    lowered = query.lower()
    scope = ["internal-knowledge-base"]
    if any(term in lowered for term in ("board", "governance", "strategy")):
        scope.append("board-documents")
    if any(term in lowered for term in ("financial", "margin", "revenue", "cost")):
        scope.append("financial-reports")
    if any(term in lowered for term in ("customer", "market", "competitor", "external")):
        scope.append("market-research")
    return _dedupe(scope)


def estimate_corpus_confidence(query: str) -> float:
    lowered = query.lower()
    if any(term in lowered for term in ("competitor", "market", "external", "latest", "news")):
        return 0.2
    return 0.8


def _expand_strategic_query(query: str) -> list[str]:
    lowered = query.lower()
    expanded = [query]
    if "risks" in lowered:
        expanded.append(f"risk drivers for {query}")
    if "opportunities" in lowered:
        expanded.append(f"opportunity drivers for {query}")
    if "competitors" in lowered:
        expanded.append(f"competitor actions related to {query}")
    return expanded


def _normalise_subquery(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip()).rstrip("?")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(value)
    return deduped

