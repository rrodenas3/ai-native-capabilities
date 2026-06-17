"""Hybrid retrieval wrapper for Cap-01 Decision Intelligence."""

from __future__ import annotations

from typing import Any, Literal

from core.memory import SemanticMemory
from core.schemas import DocumentChunk, RetrievalResult

AccessTier = Literal["public", "internal", "restricted"]

ACCESS_ORDER: dict[AccessTier, set[str]] = {
    "public": {"public"},
    "internal": {"public", "internal"},
    "restricted": {"public", "internal", "restricted"},
}


class CapabilityRetriever:
    """Capability-level retrieval with access control and result shaping."""

    def __init__(self, semantic_memory: SemanticMemory) -> None:
        self.semantic_memory = semantic_memory

    def hybrid_search(
        self,
        query: str,
        k: int = 10,
        filters: dict[str, Any] | None = None,
        access_tier: AccessTier = "internal",
    ) -> list[RetrievalResult]:
        filters = self._prepare_filters(filters, access_tier)
        chunks = self.semantic_memory.hybrid_search(query, k=k * 2, filters=filters)
        filtered = [
            chunk
            for chunk in chunks
            if self._is_authorized(chunk, access_tier) and self._matches_post_filters(chunk, filters)
        ]
        deduped = self._dedupe(filtered)
        return self._format_results(deduped[:k])

    def multi_query_search(
        self,
        queries: list[str],
        k: int = 10,
        filters: dict[str, Any] | None = None,
        access_tier: AccessTier = "internal",
    ) -> list[RetrievalResult]:
        merged: dict[str, RetrievalResult] = {}
        for query in queries:
            for result in self.hybrid_search(query, k=k, filters=filters, access_tier=access_tier):
                key = _chunk_key(result.chunk)
                if key not in merged or result.combined_score > merged[key].combined_score:
                    merged[key] = result

        ranked = sorted(merged.values(), key=lambda result: result.combined_score, reverse=True)[:k]
        for rank, result in enumerate(ranked, start=1):
            result.rank = rank
        return ranked

    def _prepare_filters(
        self,
        filters: dict[str, Any] | None,
        access_tier: AccessTier,
    ) -> dict[str, Any]:
        prepared = dict(filters or {})
        if access_tier == "restricted":
            prepared["include_restricted"] = True
        requested = prepared.get("access_tier")
        if requested is not None and requested not in ACCESS_ORDER[access_tier]:
            prepared["access_tier"] = "__unauthorized__"
        return prepared

    @staticmethod
    def _dedupe(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        seen: set[str] = set()
        deduped: list[DocumentChunk] = []
        for chunk in chunks:
            key = _chunk_key(chunk)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(chunk)
        return deduped

    @staticmethod
    def _format_results(chunks: list[DocumentChunk]) -> list[RetrievalResult]:
        results: list[RetrievalResult] = []
        for rank, chunk in enumerate(chunks, start=1):
            score = 1.0 / rank
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    semantic_score=score,
                    lexical_score=None,
                    combined_score=score,
                    rank=rank,
                )
            )
        return results

    @staticmethod
    def _is_authorized(chunk: DocumentChunk, access_tier: AccessTier) -> bool:
        return chunk.access_tier in ACCESS_ORDER[access_tier]

    @staticmethod
    def _matches_post_filters(chunk: DocumentChunk, filters: dict[str, Any]) -> bool:
        if filters.get("access_tier") == "__unauthorized__":
            return False
        author = filters.get("author")
        return not (author is not None and chunk.metadata.get("author") != author)


def _chunk_key(chunk: DocumentChunk) -> str:
    return f"{chunk.capability.value}:{chunk.doc_id}:{chunk.chunk_index}"
