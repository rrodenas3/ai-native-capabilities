from __future__ import annotations

import importlib.util
import sys
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.memory import EpisodicMemory
from core.schemas import Citation, Finding

MEMORY_PATH = Path(__file__).parents[1] / "memory" / "episodic.py"
MEMORY_SPEC = importlib.util.spec_from_file_location("cap01_episodic_memory", MEMORY_PATH)
if MEMORY_SPEC is None or MEMORY_SPEC.loader is None:
    raise RuntimeError(f"Unable to load Cap-01 episodic memory from {MEMORY_PATH}")
memory_module = importlib.util.module_from_spec(MEMORY_SPEC)
sys.modules[MEMORY_SPEC.name] = memory_module
MEMORY_SPEC.loader.exec_module(memory_module)

SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "brief.py"
schema_module = sys.modules.get("cap01_brief_schema")
if schema_module is None:
    SCHEMA_SPEC = importlib.util.spec_from_file_location("cap01_brief_schema", SCHEMA_PATH)
    if SCHEMA_SPEC is None or SCHEMA_SPEC.loader is None:
        raise RuntimeError(f"Unable to load brief schema from {SCHEMA_PATH}")
    schema_module = importlib.util.module_from_spec(SCHEMA_SPEC)
    sys.modules[SCHEMA_SPEC.name] = schema_module
    SCHEMA_SPEC.loader.exec_module(schema_module)

DecisionBriefEpisodicMemory = memory_module.DecisionBriefEpisodicMemory
StoredBrief = memory_module.StoredBrief
BriefOutput = schema_module.BriefOutput


class FakeCursor(AbstractContextManager["FakeCursor"]):
    def __init__(self, connection: "FakeConnection") -> None:
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
            self._rows = sorted(rows, key=lambda row: _distance(query_vector, _parse_test_vector(row[6])))[: params[1]]
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
    if "margin" in text.lower():
        return [0.0, 1.0, 0.0]
    return [0.0, 0.0, 1.0]


def make_memory(connection: FakeConnection) -> DecisionBriefEpisodicMemory:
    core_memory = EpisodicMemory(connection_factory=lambda: connection, embedding_fn=embedding)
    return DecisionBriefEpisodicMemory(core_memory)


def make_brief(summary: str = "Supply risk is elevated.") -> BriefOutput:
    citation = Citation(
        source_doc_id="doc-a",
        source_title="Q3 memo",
        source_date="2026-06-01",
        chunk_index=0,
        excerpt="Supply risk is elevated.",
        confidence=0.9,
    )
    return BriefOutput(
        executive_summary=summary,
        key_findings=[
            Finding(
                claim=summary,
                citations=[citation],
                confidence=0.9,
            )
        ],
        uncertainty_flags=["Competitor mitigation evidence missing"],
        recommended_actions=["Review cited source.", "Validate owner.", "Gather missing evidence."],
        overall_confidence=0.9,
    )


def test_store_brief_persists_summary_embedding_target_and_metadata() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    brief = make_brief()

    event_id = memory.store_brief(
        brief,
        "session-1",
        "run-1",
        query="supply risk",
        cost_usd=0.12,
        latency_ms=321.0,
    )

    row = connection.rows[0]
    assert event_id == str(row[0])
    assert row[1] == "cap-01"
    assert row[4] == "decision_brief.completed"
    assert row[5] == brief.executive_summary
    assert row[6] == "[1.0,0.0,0.0]"
    assert row[7]["query"] == "supply risk"
    assert row[7]["confidence"] == 0.9
    assert row[7]["cost_usd"] == 0.12
    assert row[7]["latency_ms"] == 321.0
    assert row[7]["brief"]["executive_summary"] == brief.executive_summary


def test_retrieve_similar_briefs_returns_structured_past_briefs() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    memory.store_brief(make_brief("Margin pressure is elevated."), "session-1", "run-margin", query="margin")
    memory.store_brief(make_brief("Supply risk is elevated."), "session-2", "run-supply", query="supply")

    results = memory.retrieve_similar_briefs("supply chain risk", k=1)

    assert len(results) == 1
    assert isinstance(results[0], StoredBrief)
    assert results[0].run_id == "run-supply"
    assert results[0].brief.executive_summary == "Supply risk is elevated."


def test_get_session_history_returns_newest_completed_briefs_first() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    memory.store_brief(make_brief("Old supply brief."), "session-history", "run-old", query="old")
    memory.store_brief(make_brief("New supply brief."), "session-history", "run-new", query="new")
    memory.store_brief(make_brief("Other session brief."), "other", "run-other", query="other")
    old_row = list(connection.rows[0])
    old_row[8] = datetime.now(UTC) - timedelta(days=1)
    connection.rows[0] = tuple(old_row)
    new_row = list(connection.rows[1])
    new_row[8] = datetime.now(UTC)
    connection.rows[1] = tuple(new_row)

    history = memory.get_session_history("session-history")

    assert [item.run_id for item in history] == ["run-new", "run-old"]
    assert [item.query for item in history] == ["new", "old"]


def test_invalid_numeric_metadata_returns_none() -> None:
    connection = FakeConnection()
    memory = make_memory(connection)
    memory.store_brief(make_brief(), "session-1", "run-1", cost_usd=0.1, latency_ms=2.0)
    row = list(connection.rows[0])
    metadata = dict(row[7])
    metadata["cost_usd"] = "not-a-number"
    metadata["latency_ms"] = object()
    row[7] = metadata
    connection.rows[0] = tuple(row)

    stored = memory.get_session_history("session-1")[0]

    assert stored.cost_usd is None
    assert stored.latency_ms is None


def _parse_test_vector(value: str) -> list[float]:
    return [float(item) for item in value.strip("[]").split(",")]


def _distance(left: list[float], right: list[float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))
