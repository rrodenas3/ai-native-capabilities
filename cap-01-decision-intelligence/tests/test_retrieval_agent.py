from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from core.schemas import AuditEvent, CapabilityID, DocumentChunk, RetrievalResult
from core.utils.settings import get_settings

MODULE_PATH = Path(__file__).parents[1] / "agents" / "retrieval_agent.py"
SPEC = importlib.util.spec_from_file_location("cap01_retrieval_agent", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

build_retrieval_agent = module.build_retrieval_agent


class FakeRetriever:
    def __init__(self) -> None:
        self.calls = []

    def hybrid_search(self, query: str, k: int = 10, filters=None, access_tier: str = "internal"):
        self.calls.append({"query": query, "k": k, "filters": filters, "access_tier": access_tier})
        return RESULTS_BY_QUERY.get(query, [])


def result(doc_id: str, score: float, rank: int = 1) -> RetrievalResult:
    return RetrievalResult(
        chunk=DocumentChunk(
            capability=CapabilityID.DECISION_INTELLIGENCE,
            doc_id=doc_id,
            chunk_index=0,
            content=f"{doc_id} content",
        ),
        semantic_score=score,
        lexical_score=None,
        combined_score=score,
        rank=rank,
    )


RESULTS_BY_QUERY = {
    "supply risk": [result("a", 0.8), result("b", 0.5)],
    "supplier exposure": [result("a", 0.9), result("c", 0.4)],
}


def base_state(**overrides):
    state = {
        "run_id": "run-1",
        "session_id": "session-1",
        "query": "supply risk",
        "sub_queries": ["supply risk", "supplier exposure"],
        "corpus_scope": ["internal-knowledge-base"],
        "corpus_confidence": 0.8,
        "agent_hops": [],
        "audit_trail": [],
    }
    state.update(overrides)
    return state


def test_retrieval_agent_executes_each_sub_query(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    retriever = FakeRetriever()

    output = build_retrieval_agent(retriever)(base_state())

    assert [call["query"] for call in retriever.calls] == ["supply risk", "supplier exposure"]
    assert [result.chunk.doc_id for result in output["retrieval_results"]] == ["a", "b", "c"]


def test_retrieval_agent_keeps_highest_score_for_duplicate(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = build_retrieval_agent(FakeRetriever())(base_state())

    top = output["retrieval_results"][0]
    assert top.chunk.doc_id == "a"
    assert top.combined_score == 0.9
    assert [result.rank for result in output["retrieval_results"]] == [1, 2, 3]


def test_retrieval_agent_passes_corpus_scope_and_access_tier(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    retriever = FakeRetriever()

    build_retrieval_agent(retriever)(
        base_state(access_tier="restricted", retrieval_filters={"doc_type": "strategy"})
    )

    assert retriever.calls[0]["access_tier"] == "restricted"
    assert retriever.calls[0]["filters"]["doc_type"] == "strategy"
    assert retriever.calls[0]["filters"]["corpus_scope"] == ["internal-knowledge-base"]


def test_retrieval_agent_routes_web_research_below_threshold(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = build_retrieval_agent(FakeRetriever())(base_state(corpus_confidence=0.2))

    assert output["web_research_required"] is True
    assert output["next_agents"] == ["web_research"]


def test_retrieval_agent_logs_audit_event(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = build_retrieval_agent(FakeRetriever())(base_state())

    assert isinstance(output["audit_trail"][0], AuditEvent)
    assert output["audit_trail"][0].event_type == "retrieval.completed"

