from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

from core.memory import Document, SemanticMemory
from core.schemas.base import CapabilityID


class FakeCursor(AbstractContextManager["FakeCursor"]):
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self._rows: list[tuple[Any, ...]] = []

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("insert into document_chunks"):
            self.connection.rows.append(params)
            return

        rows = self.connection.apply_filters(params)
        if "order by embedding <=>" in normalized:
            query_vector = _parse_test_vector(params[-2])
            self._rows = sorted(
                [row for row in rows if row[5] is not None],
                key=lambda row: _distance(query_vector, _parse_test_vector(row[5])),
            )[: params[-1]]
            return

        if "order by created_at desc" in normalized:
            self._rows = sorted(rows, key=lambda row: row[8], reverse=True)
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

    def apply_filters(self, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
        rows = list(self.rows)
        if not params:
            return rows

        allowed_tiers = params[0]
        rows = [row for row in rows if row[7] in allowed_tiers]
        remaining = list(params[1:])

        if remaining and isinstance(remaining[0], str) and not remaining[0].startswith("["):
            doc_type = remaining.pop(0)
            rows = [row for row in rows if row[6].get("doc_type") == doc_type]

        if len(remaining) >= 2 and not str(remaining[0]).startswith("["):
            start, end = remaining[0], remaining[1]
            rows = [row for row in rows if start <= row[6].get("date") <= end]

        return rows


def embedding(text: str) -> list[float]:
    lowered = text.lower()
    if "supply" in lowered:
        return [1.0, 0.0, 0.0]
    if "compliance" in lowered:
        return [0.0, 1.0, 0.0]
    return [0.0, 0.0, 1.0]


def make_memory(connection: FakeConnection) -> SemanticMemory:
    return SemanticMemory(
        connection_factory=lambda: connection,
        embedding_fn=embedding,
        chunk_tokens=6,
        chunk_overlap=2,
    )


def test_index_chunks_embeds_and_writes_documents() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)

    memory.index(
        [
            Document(
                doc_id="doc-1",
                capability=CapabilityID.DECISION_INTELLIGENCE,
                content="one two three four five six seven eight nine",
                metadata={"doc_type": "strategy", "date": "2026-06-01"},
                access_tier="internal",
            )
        ]
    )

    assert connection.commits == 1
    assert len(connection.rows) == 2
    assert connection.rows[0][1] == "cap-01"
    assert connection.rows[0][6]["doc_type"] == "strategy"


def test_search_returns_semantic_top_k() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    index_sample_documents(memory)

    results = memory.search("supply forecast", k=1)

    assert len(results) == 1
    assert results[0].doc_id == "supply"


def test_hybrid_search_combines_semantic_and_bm25() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    index_sample_documents(memory)

    results = memory.hybrid_search("supplier lead time supply", k=2)

    assert results[0].doc_id == "supply"
    assert len(results) == 2


def test_filters_doc_type_and_date_range() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    index_sample_documents(memory)

    results = memory.search(
        "compliance",
        filters={"doc_type": "regulatory", "date_range": ("2026-01-01", "2026-12-31")},
    )

    assert [chunk.doc_id for chunk in results] == ["compliance"]


def test_restricted_docs_are_hidden_by_default() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    index_sample_documents(memory)

    results = memory.search("secret supply", k=10)

    assert "restricted" not in {chunk.doc_id for chunk in results}


def test_restricted_docs_require_authorized_filter() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    index_sample_documents(memory)

    results = memory.search("secret supply", filters={"include_restricted": True})

    assert "restricted" in {chunk.doc_id for chunk in results}


def index_sample_documents(memory: SemanticMemory) -> None:
    memory.index(
        [
            Document(
                doc_id="supply",
                capability="cap-01",
                content="supply forecast supplier lead time inventory",
                metadata={"doc_type": "strategy", "date": "2026-06-01"},
                access_tier="internal",
            ),
            Document(
                doc_id="compliance",
                capability="cap-05",
                content="compliance obligation regulatory article review",
                metadata={"doc_type": "regulatory", "date": "2026-05-01"},
                access_tier="public",
            ),
            Document(
                doc_id="restricted",
                capability="cap-01",
                content="secret supply contract margin",
                metadata={"doc_type": "contract", "date": "2026-06-02"},
                access_tier="restricted",
            ),
        ]
    )


def _parse_test_vector(value: str) -> list[float]:
    return [float(item) for item in value.strip("[]").split(",")]


def _distance(left: list[float], right: list[float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))
