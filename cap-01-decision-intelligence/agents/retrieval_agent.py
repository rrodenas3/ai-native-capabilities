"""Retrieval agent for Cap-01 Decision Intelligence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from core.schemas import AgentHop, AgentHopType, AuditEvent, CapabilityID, RetrievalResult
from core.utils.settings import get_settings

WEB_CONFIDENCE_THRESHOLD = 0.3


class Retriever(Protocol):
    def hybrid_search(
        self,
        query: str,
        k: int = 10,
        filters: dict[str, Any] | None = None,
        access_tier: str = "internal",
    ) -> list[RetrievalResult]: ...


def build_retrieval_agent(retriever: Retriever, *, k_per_query: int = 10) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def retrieval_agent_node(state: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        sub_queries = list(state.get("sub_queries") or [state.get("query", "")])
        access_tier = str(state.get("access_tier", "internal"))
        filters = _filters_from_state(state)
        results: list[RetrievalResult] = []
        for query in sub_queries:
            if not query:
                continue
            results.extend(
                retriever.hybrid_search(
                    str(query),
                    k=k_per_query,
                    filters=filters,
                    access_tier=access_tier,
                )
            )

        ranked = _dedupe_and_rank(results)
        corpus_confidence = float(state.get("corpus_confidence", 1.0))
        web_research_required = corpus_confidence < WEB_CONFIDENCE_THRESHOLD
        hop = AgentHop(
            agent_name="retrieval",
            hop_type=AgentHopType.RETRIEVAL,
            model=settings.LLM_FAST,
            confidence=corpus_confidence,
            success=True,
        )
        audit_event = AuditEvent(
            capability=CapabilityID.DECISION_INTELLIGENCE,
            run_id=str(state.get("run_id", "")),
            session_id=str(state.get("session_id", "")),
            event_type="retrieval.completed",
            agent_name="retrieval",
            action="hybrid_search",
            payload={
                "sub_queries": sub_queries,
                "result_count": len(ranked),
                "corpus_scope": state.get("corpus_scope", []),
                "web_research_required": web_research_required,
            },
        )
        return {
            **state,
            "current_agent": "retrieval",
            "retrieval_results": ranked,
            "web_research_required": web_research_required,
            "next_agents": ["web_research"] if web_research_required else ["analysis"],
            "agent_hops": [*state.get("agent_hops", []), hop],
            "audit_trail": [*state.get("audit_trail", []), audit_event],
        }

    return retrieval_agent_node


def _filters_from_state(state: dict[str, Any]) -> dict[str, Any]:
    filters = dict(state.get("retrieval_filters", {}))
    corpus_scope = state.get("corpus_scope")
    if corpus_scope:
        filters["corpus_scope"] = list(corpus_scope)
    return filters


def _dedupe_and_rank(results: list[RetrievalResult]) -> list[RetrievalResult]:
    merged: dict[str, RetrievalResult] = {}
    for result in results:
        key = _result_key(result)
        if key not in merged or result.combined_score > merged[key].combined_score:
            merged[key] = result
    ranked = sorted(merged.values(), key=lambda result: result.combined_score, reverse=True)
    for rank, result in enumerate(ranked, start=1):
        result.rank = rank
    return ranked


def _result_key(result: RetrievalResult) -> str:
    chunk = result.chunk
    return f"{chunk.capability.value}:{chunk.doc_id}:{chunk.chunk_index}"

