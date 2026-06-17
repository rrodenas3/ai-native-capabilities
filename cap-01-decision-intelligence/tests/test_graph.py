from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver

from core.schemas import CapabilityID, DocumentChunk, RetrievalResult
from core.utils.settings import get_settings

MODULE_PATH = Path(__file__).parents[1] / "agents" / "graph.py"
SPEC = importlib.util.spec_from_file_location("cap01_graph", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load graph module from {MODULE_PATH}")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

build_graph = module.build_graph
build_postgres_checkpointer = module.build_postgres_checkpointer
initial_state = module.initial_state
DecisionBriefState = module.DecisionBriefState


class FakeRetriever:
    def hybrid_search(self, query: str, k: int = 10, filters=None, access_tier: str = "internal"):
        return [
            result(
                "doc-a",
                f"{query} is addressed by supplier concentration evidence and margin pressure analysis.",
                0.9,
                rank=1,
            ),
            result(
                "doc-b",
                "Board materials show mitigation options, owner accountability, and operating risk tradeoffs.",
                0.75,
                rank=2,
            ),
        ][:k]


def result(doc_id: str, content: str, score: float, *, rank: int) -> RetrievalResult:
    return RetrievalResult(
        chunk=DocumentChunk(
            capability=CapabilityID.DECISION_INTELLIGENCE,
            doc_id=doc_id,
            chunk_index=rank - 1,
            content=content,
            metadata={"title": f"{doc_id} title", "date": "2026-06-01"},
            access_tier="internal",
        ),
        semantic_score=score,
        lexical_score=None,
        combined_score=score,
        rank=rank,
    )


def configure_mock_human_gate(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("EVAL_MODE", "ci")
    monkeypatch.setenv("HUMAN_GATE_MOCK_APPROVED", "true")
    get_settings.cache_clear()


def test_build_graph_returns_compiled_state_graph(monkeypatch) -> None:
    configure_mock_human_gate(monkeypatch)

    graph = build_graph(FakeRetriever(), checkpointer=MemorySaver())

    assert graph is not None
    assert DecisionBriefState.__name__ == "DecisionBriefState"


def test_graph_completes_end_to_end_and_logs_audit(monkeypatch) -> None:
    configure_mock_human_gate(monkeypatch)
    graph = build_graph(FakeRetriever(), checkpointer=MemorySaver())

    output = graph.invoke(
        initial_state(
            "What are supply chain risks entering Q3?",
            run_id="run-graph-1",
            session_id="session-graph-1",
        ),
        config={"configurable": {"thread_id": "run-graph-1"}},
    )

    assert output["human_approved"] is True
    assert output["executive_summary"]
    assert output["key_findings"]
    assert output["overall_confidence"] > 0
    assert output["cost_telemetry"]["hop_count"] >= 5
    event_types = [event.event_type for event in output["audit_trail"]]
    assert "brief.completed" in event_types
    assert "human_gate.approved" in event_types
    assert event_types.count("graph.transition") >= 6


def test_graph_completes_for_10_diverse_queries_under_30s(monkeypatch) -> None:
    configure_mock_human_gate(monkeypatch)
    graph = build_graph(FakeRetriever(), checkpointer=MemorySaver())
    queries = [
        "What are our Q3 supply risks?",
        "Where are margin opportunities in enterprise accounts?",
        "Summarize board concerns and compliance gaps",
        "What changed in customer retention?",
        "Which competitors responded to pricing pressure?",
        "Assess revenue risk and cost exposure",
        "What operating risks affect Europe expansion?",
        "Identify gaps in the AI governance plan",
        "What are the latest market signals?",
        "Which documents support the hiring plan?",
    ]

    outputs = [
        graph.invoke(
            initial_state(query, run_id=f"run-{index}", session_id=f"session-{index}"),
            config={"configurable": {"thread_id": f"run-{index}"}},
        )
        for index, query in enumerate(queries, start=1)
    ]

    assert len(outputs) == 10
    assert all(output["executive_summary"] for output in outputs)
    assert all(output["human_approved"] is True for output in outputs)
    assert all(output["latency_ms"] <= 30_000 for output in outputs)


def test_postgres_checkpointer_factory_is_context_manager() -> None:
    manager = build_postgres_checkpointer("postgresql://localhost:5432/ai_native")

    assert hasattr(manager, "__enter__")
    assert hasattr(manager, "__exit__")


def test_postgres_checkpointer_rejects_invalid_url() -> None:
    with pytest.raises(ValueError, match="Invalid PostgreSQL connection string"):
        with build_postgres_checkpointer("sqlite://local"):
            pass


def test_graph_records_error_state_when_node_fails(monkeypatch) -> None:
    configure_mock_human_gate(monkeypatch)

    class FailingRetriever:
        def hybrid_search(self, query: str, k: int = 10, filters=None, access_tier: str = "internal"):
            raise RuntimeError("retriever unavailable")

    graph = build_graph(FailingRetriever(), checkpointer=MemorySaver())

    output = graph.invoke(
        initial_state("What are supply chain risks?", run_id="run-error", session_id="session-error"),
        config={"configurable": {"thread_id": "run-error"}},
    )

    assert output["error_state"]["node"] == "retrieval"
    assert output["error_state"]["error_type"] == "RuntimeError"
    assert any(event.action == "node_failed" for event in output["audit_trail"])
