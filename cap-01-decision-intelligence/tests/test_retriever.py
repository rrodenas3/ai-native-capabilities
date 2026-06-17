from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from core.schemas import CapabilityID, DocumentChunk, RetrievalResult

MODULE_PATH = Path(__file__).parents[1] / "tools" / "retriever.py"
SPEC = importlib.util.spec_from_file_location("cap01_retriever", MODULE_PATH)
assert SPEC and SPEC.loader
retriever_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = retriever_module
SPEC.loader.exec_module(retriever_module)

CapabilityRetriever = retriever_module.CapabilityRetriever


class FakeSemanticMemory:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks
        self.calls = []

    def hybrid_search(self, query: str, k: int = 10, filters=None):
        self.calls.append({"query": query, "k": k, "filters": filters})
        return list(self.chunks)[:k]


def chunk(
    doc_id: str,
    index: int = 0,
    *,
    access_tier: str = "internal",
    metadata=None,
) -> DocumentChunk:
    return DocumentChunk(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        doc_id=doc_id,
        chunk_index=index,
        content=f"{doc_id} content",
        metadata=metadata or {},
        access_tier=access_tier,
    )


def test_hybrid_search_returns_retrieval_results() -> None:
    retriever = CapabilityRetriever(FakeSemanticMemory([chunk("a"), chunk("b")]))

    results = retriever.hybrid_search("risk", k=2)

    assert all(isinstance(result, RetrievalResult) for result in results)
    assert [result.rank for result in results] == [1, 2]
    assert results[0].combined_score > results[1].combined_score


def test_restricted_docs_hidden_from_internal_callers() -> None:
    retriever = CapabilityRetriever(
        FakeSemanticMemory([chunk("public", access_tier="public"), chunk("secret", access_tier="restricted")])
    )

    results = retriever.hybrid_search("risk", access_tier="internal")

    assert [result.chunk.doc_id for result in results] == ["public"]


def test_restricted_docs_returned_to_restricted_callers() -> None:
    memory = FakeSemanticMemory([chunk("secret", access_tier="restricted")])
    retriever = CapabilityRetriever(memory)

    results = retriever.hybrid_search("risk", access_tier="restricted")

    assert [result.chunk.doc_id for result in results] == ["secret"]
    assert memory.calls[0]["filters"]["include_restricted"] is True


def test_unauthorized_access_tier_filter_returns_no_results() -> None:
    retriever = CapabilityRetriever(FakeSemanticMemory([chunk("secret", access_tier="restricted")]))

    results = retriever.hybrid_search("risk", filters={"access_tier": "restricted"}, access_tier="public")

    assert results == []


def test_author_metadata_filter_is_enforced() -> None:
    retriever = CapabilityRetriever(
        FakeSemanticMemory(
            [
                chunk("match", metadata={"author": "ops"}),
                chunk("miss", metadata={"author": "finance"}),
            ]
        )
    )

    results = retriever.hybrid_search("risk", filters={"author": "ops"})

    assert [result.chunk.doc_id for result in results] == ["match"]


def test_duplicate_chunks_are_returned_once() -> None:
    repeated = chunk("a", 0)
    retriever = CapabilityRetriever(FakeSemanticMemory([repeated, repeated, chunk("b", 0)]))

    results = retriever.hybrid_search("risk", k=10)

    assert [result.chunk.doc_id for result in results] == ["a", "b"]


def test_multi_query_search_deduplicates_and_reranks() -> None:
    repeated = chunk("a", 0)
    retriever = CapabilityRetriever(FakeSemanticMemory([repeated, chunk("b", 0), repeated]))

    results = retriever.multi_query_search(["risk", "supplier"], k=2)

    assert [result.chunk.doc_id for result in results] == ["a", "b"]
    assert [result.rank for result in results] == [1, 2]

