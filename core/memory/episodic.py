"""Episodic memory backed by PostgreSQL + pgvector."""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID

import psycopg

from core.schemas.base import CapabilityID, MemoryEvent

EmbeddingFunction = Callable[[str], list[float]]


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ...) -> Any: ...
    def fetchall(self) -> list[Any]: ...


class Connection(Protocol):
    def cursor(self) -> Any: ...
    def commit(self) -> None: ...


ConnectionFactory = Callable[[], Connection]


class EpisodicMemory:
    """Store and retrieve past agent events."""

    def __init__(
        self,
        connection_factory: ConnectionFactory | None = None,
        embedding_fn: EmbeddingFunction | None = None,
        *,
        database_url: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self.embedding_fn = embedding_fn
        self.embedding_model = embedding_model or os.getenv("LLM_EMBEDDINGS", "text-embedding-3-large")
        self._connection_factory = connection_factory or self._default_connection_factory(database_url)

    def store(self, event: MemoryEvent) -> str:
        """Store an event in the episodic memory table."""

        event_to_store = event.model_copy()
        if event_to_store.embedding is None and self.embedding_fn is not None:
            event_to_store.embedding = self.embedding_fn(event_to_store.content)

        embedding = _format_vector(event_to_store.embedding)
        event_id = str(event_to_store.event_id)
        connection = self._connection_factory()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO episodic_memory
                    (id, capability, session_id, run_id, event_type, content, embedding, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    _capability_value(event_to_store.capability),
                    event_to_store.session_id,
                    event_to_store.run_id,
                    event_to_store.event_type,
                    event_to_store.content,
                    embedding,
                    event_to_store.metadata,
                    event_to_store.created_at,
                ),
            )
        connection.commit()
        return event_id

    def retrieve_similar(self, query: str, k: int = 5) -> list[MemoryEvent]:
        """Return the top-k events most similar to the query."""

        if k < 1:
            return []

        query_embedding = self.embedding_fn(query) if self.embedding_fn is not None else None
        if query_embedding is None:
            return self._retrieve_lexical(query, k)

        rows = self._fetch_similar_by_vector(query_embedding, k)
        return [_row_to_memory_event(row) for row in rows]

    def get_session_history(self, session_id: str) -> list[MemoryEvent]:
        """Return events for a session ordered by newest first."""

        with self._connection_factory().cursor() as cursor:
            cursor.execute(
                """
                SELECT id, capability, session_id, run_id, event_type, content, embedding, metadata, created_at
                FROM episodic_memory
                WHERE session_id = %s
                ORDER BY created_at DESC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()
        return [_row_to_memory_event(row) for row in rows]

    def _fetch_similar_by_vector(self, query_embedding: list[float], k: int) -> list[Any]:
        with self._connection_factory().cursor() as cursor:
            cursor.execute(
                """
                SELECT id, capability, session_id, run_id, event_type, content, embedding, metadata, created_at
                FROM episodic_memory
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (_format_vector(query_embedding), k),
            )
            rows = cursor.fetchall()
        return rows

    def _retrieve_lexical(self, query: str, k: int) -> list[MemoryEvent]:
        with self._connection_factory().cursor() as cursor:
            cursor.execute(
                """
                SELECT id, capability, session_id, run_id, event_type, content, embedding, metadata, created_at
                FROM episodic_memory
                ORDER BY created_at DESC
                """,
            )
            rows = cursor.fetchall()

        query_terms = set(query.lower().split())
        ranked = sorted(
            rows,
            key=lambda row: _lexical_score(query_terms, str(row[5])),
            reverse=True,
        )
        return [_row_to_memory_event(row) for row in ranked[:k]]

    @staticmethod
    def _default_connection_factory(database_url: str | None) -> ConnectionFactory:
        resolved_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/ai_native",
        )
        return lambda: psycopg.connect(resolved_url)


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


def _capability_value(value: CapabilityID | str) -> str:
    return value.value if isinstance(value, CapabilityID) else value


def _row_to_memory_event(row: Any) -> MemoryEvent:
    return MemoryEvent(
        event_id=UUID(str(row[0])),
        capability=CapabilityID(row[1]),
        session_id=row[2],
        run_id=row[3],
        event_type=row[4],
        content=row[5],
        embedding=_parse_vector(row[6]),
        metadata=row[7] or {},
        created_at=row[8],
    )


def _lexical_score(query_terms: set[str], content: str) -> float:
    if not query_terms:
        return 0.0
    content_terms = set(content.lower().split())
    overlap = len(query_terms & content_terms)
    return overlap / math.sqrt(max(len(content_terms), 1))
