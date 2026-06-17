from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from typing import Any

from core.memory import EpisodicMemory
from core.schemas.base import CapabilityID, MemoryEvent


class FakeCursor(AbstractContextManager["FakeCursor"]):
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self._rows: list[tuple[Any, ...]] = []

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("insert into episodic_memory"):
            self.connection.rows.append(params)
            return

        if "where session_id = %s" in normalized:
            session_id = params[0]
            rows = [row for row in self.connection.rows if row[2] == session_id]
            self._rows = sorted(rows, key=lambda row: row[8], reverse=True)
            return

        if "order by embedding <=>" in normalized:
            query_vector = _parse_test_vector(params[0])
            rows = [row for row in self.connection.rows if row[6] is not None]
            self._rows = sorted(
                rows,
                key=lambda row: _distance(query_vector, _parse_test_vector(row[6])),
            )[: params[1]]
            return

        if "order by created_at desc" in normalized:
            self._rows = sorted(self.connection.rows, key=lambda row: row[8], reverse=True)
            return

        raise AssertionError(f"unexpected SQL: {query}")

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class FakeConnection:
    def __init__(self) -> None:
        self.rows: list[tuple[Any, ...]] = []
        self.commits = 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1


def embedding(text: str) -> list[float]:
    if "supply" in text.lower():
        return [1.0, 0.0, 0.0]
    if "compliance" in text.lower():
        return [0.0, 1.0, 0.0]
    return [0.0, 0.0, 1.0]


def make_memory(connection: FakeConnection) -> EpisodicMemory:
    return EpisodicMemory(connection_factory=lambda: connection, embedding_fn=embedding)


def make_event(content: str, session_id: str = "session-1") -> MemoryEvent:
    return MemoryEvent(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        session_id=session_id,
        run_id="run-1",
        event_type="brief.created",
        content=content,
        metadata={"source": "test"},
    )


def test_store_writes_memory_event_and_generates_embedding() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    event = make_event("Supply chain risk summary")

    event_id = memory.store(event)

    assert event_id == str(event.event_id)
    assert connection.commits == 1
    row = connection.rows[0]
    assert row[1] == "cap-01"
    assert row[5] == "Supply chain risk summary"
    assert row[6] == "[1.0,0.0,0.0]"
    assert row[7] == {"source": "test"}


def test_retrieve_similar_uses_vector_ordering() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    memory.store(make_event("Compliance obligation summary"))
    memory.store(make_event("Supply chain risk summary"))

    results = memory.retrieve_similar("supply question", k=1)

    assert len(results) == 1
    assert results[0].content == "Supply chain risk summary"


def test_get_session_history_orders_newest_first() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    old_event = make_event("old", session_id="session-history")
    old_event.created_at = datetime.now(UTC) - timedelta(days=1)
    new_event = make_event("new", session_id="session-history")
    new_event.created_at = datetime.now(UTC)
    memory.store(old_event)
    memory.store(new_event)
    memory.store(make_event("other", session_id="other"))

    results = memory.get_session_history("session-history")

    assert [event.content for event in results] == ["new", "old"]


def test_retrieve_similar_returns_empty_for_invalid_k() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)

    assert memory.retrieve_similar("supply", k=0) == []


def test_retrieve_similar_can_fallback_to_lexical_search() -> None:
    connection = FakeConnection()
    memory = EpisodicMemory(connection_factory=lambda: connection)
    memory.store(make_event("pricing decision"))
    memory.store(make_event("supply decision"))

    results = memory.retrieve_similar("supply", k=1)

    assert results[0].content == "supply decision"


def test_embedding_model_is_configurable_without_hardcoding(monkeypatch) -> None:
    monkeypatch.setenv("LLM_EMBEDDINGS", "test-embedding-model")
    memory = EpisodicMemory(connection_factory=lambda: FakeConnection())

    assert memory.embedding_model == "test-embedding-model"


def _parse_test_vector(value: str) -> list[float]:
    return [float(item) for item in value.strip("[]").split(",")]


def _distance(left: list[float], right: list[float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))
