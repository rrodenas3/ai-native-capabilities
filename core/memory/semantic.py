"""Semantic memory backed by PostgreSQL + pgvector and BM25."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal
from uuid import UUID

import psycopg
from rank_bm25 import BM25Okapi

from core.memory.episodic import ConnectionFactory
from core.schemas.base import CapabilityID, DocumentChunk

EmbeddingFunction = Callable[[str], list[float]]
AccessTier = Literal["public", "internal", "restricted"]


@dataclass(slots=True)
class Document:
    doc_id: str
    content: str
    capability: CapabilityID | str
    metadata: dict[str, Any] = field(default_factory=dict)
    access_tier: AccessTier = "internal"


class SemanticMemory:
    """Document chunk index with semantic and hybrid retrieval."""

    def __init__(
        self,
        connection_factory: ConnectionFactory | None = None,
        embedding_fn: EmbeddingFunction | None = None,
        *,
        database_url: str | None = None,
        chunk_tokens: int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        if chunk_tokens <= chunk_overlap:
            raise ValueError("chunk_tokens must be greater than chunk_overlap")
        self.embedding_fn = embedding_fn
        self.chunk_tokens = chunk_tokens
        self.chunk_overlap = chunk_overlap
        self._connection_factory = connection_factory or self._default_connection_factory(database_url)

    def index(self, documents: list[Document]) -> None:
        """Chunk, embed, and write documents to ``document_chunks``."""

        connection = self._connection_factory()
        with connection.cursor() as cursor:
            for document in documents:
                for index, content in enumerate(
                    _chunk_text(document.content, self.chunk_tokens, self.chunk_overlap)
                ):
                    chunk = DocumentChunk(
                        capability=CapabilityID(_capability_value(document.capability)),
                        doc_id=document.doc_id,
                        chunk_index=index,
                        content=content,
                        embedding=self.embedding_fn(content) if self.embedding_fn else None,
                        metadata=document.metadata,
                        access_tier=document.access_tier,
                    )
                    cursor.execute(
                        """
                        INSERT INTO document_chunks
                            (id, capability, doc_id, chunk_index, content, embedding, metadata, access_tier, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (capability, doc_id, chunk_index) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            access_tier = EXCLUDED.access_tier,
                            created_at = EXCLUDED.created_at
                        """,
                        (
                            str(chunk.chunk_id),
                            _capability_value(chunk.capability),
                            chunk.doc_id,
                            chunk.chunk_index,
                            chunk.content,
                            _format_vector(chunk.embedding),
                            chunk.metadata,
                            chunk.access_tier,
                            chunk.created_at,
                        ),
                    )
        connection.commit()

    def search(
        self,
        query: str,
        k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Run pure semantic search with pgvector cosine ordering."""

        if k < 1:
            return []
        query_embedding = self.embedding_fn(query) if self.embedding_fn else None
        if query_embedding is None:
            return self._filtered_chunks(filters)[:k]

        rows = self._fetch_semantic_rows(query_embedding, k, filters)
        return [_row_to_document_chunk(row) for row in rows]

    def hybrid_search(
        self,
        query: str,
        k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Combine semantic search and BM25 with reciprocal-rank fusion."""

        if k < 1:
            return []

        semantic = self.search(query, k=max(k * 2, 10), filters=filters)
        candidates = self._filtered_chunks(filters)
        lexical = _bm25_rank(query, candidates)

        fused_scores: dict[str, float] = {}
        chunks: dict[str, DocumentChunk] = {}
        for rank, chunk in enumerate(semantic, start=1):
            key = _chunk_key(chunk)
            chunks[key] = chunk
            fused_scores[key] = fused_scores.get(key, 0.0) + _rrf_score(rank)
        for rank, chunk in enumerate(lexical, start=1):
            key = _chunk_key(chunk)
            chunks[key] = chunk
            fused_scores[key] = fused_scores.get(key, 0.0) + _rrf_score(rank)

        return [
            chunks[key]
            for key, _score in sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
        ][:k]

    def _fetch_semantic_rows(
        self,
        query_embedding: list[float],
        k: int,
        filters: dict[str, Any] | None,
    ) -> list[Any]:
        clauses, params = _filter_clauses(filters)
        clauses.append("embedding IS NOT NULL")
        where = " WHERE " + " AND ".join(clauses)
        params.extend([_format_vector(query_embedding), k])
        with self._connection_factory().cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, capability, doc_id, chunk_index, content, embedding, metadata, access_tier, created_at
                FROM document_chunks
                {where}
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                tuple(params),
            )
            return cursor.fetchall()

    def _filtered_chunks(self, filters: dict[str, Any] | None) -> list[DocumentChunk]:
        clauses, params = _filter_clauses(filters)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connection_factory().cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, capability, doc_id, chunk_index, content, embedding, metadata, access_tier, created_at
                FROM document_chunks
                {where}
                ORDER BY created_at DESC
                """,
                tuple(params),
            )
            rows = cursor.fetchall()
        return [_row_to_document_chunk(row) for row in rows]

    @staticmethod
    def _default_connection_factory(database_url: str | None) -> ConnectionFactory:
        resolved_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://localhost:5432/ai_native",
        )
        return lambda: psycopg.connect(resolved_url)


def _filter_clauses(filters: dict[str, Any] | None) -> tuple[list[str], list[Any]]:
    filters = filters or {}
    authorized = bool(filters.get("include_restricted", False))
    requested_tier = filters.get("access_tier")
    allowed_tiers = ["public", "internal"] if not authorized else ["public", "internal", "restricted"]
    if requested_tier is not None:
        allowed_tiers = [requested_tier] if requested_tier in allowed_tiers else []

    clauses = ["access_tier = ANY(%s)"]
    params: list[Any] = [allowed_tiers]

    doc_type = filters.get("doc_type")
    if doc_type is not None:
        clauses.append("metadata->>'doc_type' = %s")
        params.append(doc_type)

    date_range = filters.get("date_range")
    if date_range is not None:
        start, end = date_range
        clauses.append("(metadata->>'date')::date BETWEEN %s AND %s")
        params.extend([_as_date(start), _as_date(end)])

    return clauses, params


def _chunk_text(text: str, chunk_tokens: int, chunk_overlap: int) -> list[str]:
    tokens = text.split()
    if not tokens:
        return []
    chunks: list[str] = []
    step = chunk_tokens - chunk_overlap
    for start in range(0, len(tokens), step):
        chunk = tokens[start : start + chunk_tokens]
        if chunk:
            chunks.append(" ".join(chunk))
        if start + chunk_tokens >= len(tokens):
            break
    return chunks


def _bm25_rank(query: str, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    if not chunks:
        return []
    corpus = [chunk.content.lower().split() for chunk in chunks]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query.lower().split())
    return [
        chunk
        for chunk, _score in sorted(zip(chunks, scores, strict=True), key=lambda item: item[1], reverse=True)
    ]


def _rrf_score(rank: int, constant: int = 60) -> float:
    return 1.0 / (constant + rank)


def _chunk_key(chunk: DocumentChunk) -> str:
    return f"{chunk.capability.value}:{chunk.doc_id}:{chunk.chunk_index}"


def _format_vector(vector: list[float] | None) -> str | None:
    if vector is None:
        return None
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def _parse_vector(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip("[]")
        if not stripped:
            return []
        return [float(item) for item in stripped.split(",")]
    return list(value)


def _row_to_document_chunk(row: Any) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=UUID(str(row[0])),
        capability=CapabilityID(row[1]),
        doc_id=row[2],
        chunk_index=row[3],
        content=row[4],
        embedding=_parse_vector(row[5]),
        metadata=row[6] or {},
        access_tier=row[7],
        created_at=row[8],
    )


def _capability_value(value: CapabilityID | str) -> str:
    return value.value if isinstance(value, CapabilityID) else value


def _as_date(value: date | str) -> date | str:
    return value
