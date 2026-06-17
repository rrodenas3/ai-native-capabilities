from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

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
initial_state = module.initial_state


class FakeRetriever:
    def hybrid_search(self, query: str, k: int = 10, filters=None, access_tier: str = "internal"):
        return [
            RetrievalResult(
                chunk=DocumentChunk(
                    capability=CapabilityID.DECISION_INTELLIGENCE,
                    doc_id="doc-a",
                    chunk_index=0,
                    content=f"{query} is supported by supply risk evidence.",
                    metadata={"title": "Decision memo", "date": "2026-06-01"},
                ),
                semantic_score=0.9,
                lexical_score=None,
                combined_score=0.9,
                rank=1,
            )
        ]


class FakeBriefMemory:
    def __init__(self) -> None:
        self.calls = []

    def store_brief(self, *args, **kwargs) -> str:
        self.calls.append({"args": args, "kwargs": kwargs})
        return "memory-event-1"


def configure_interrupt_mode(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.delenv("EVAL_MODE", raising=False)
    monkeypatch.delenv("HUMAN_GATE_MOCK_APPROVED", raising=False)
    get_settings.cache_clear()


def test_graph_pauses_at_human_gate_interrupt(monkeypatch) -> None:
    configure_interrupt_mode(monkeypatch)
    graph = build_graph(FakeRetriever(), checkpointer=MemorySaver(), episodic_memory=FakeBriefMemory())

    output = graph.invoke(
        initial_state("What are Q3 supply risks?", run_id="run-pause", session_id="session-pause"),
        config={"configurable": {"thread_id": "run-pause"}},
    )

    assert "__interrupt__" in output
    interrupt_payload = output["__interrupt__"][0].value
    assert interrupt_payload["type"] == "human_approval_required"
    assert interrupt_payload["run_id"] == "run-pause"


def test_approval_resume_stores_brief_and_logs_decision(monkeypatch) -> None:
    configure_interrupt_mode(monkeypatch)
    memory = FakeBriefMemory()
    graph = build_graph(FakeRetriever(), checkpointer=MemorySaver(), episodic_memory=memory)
    config = {"configurable": {"thread_id": "run-approve"}}
    graph.invoke(initial_state("What are Q3 supply risks?", run_id="run-approve", session_id="session-approve"), config=config)

    output = graph.invoke(
        Command(resume={"status": "approved", "approver_id": "board-chair", "rationale": "Sources reviewed"}),
        config=config,
    )

    assert output["human_approved"] is True
    assert output["brief_stored"] is True
    assert output["brief_memory_event_id"] == "memory-event-1"
    assert memory.calls[0]["kwargs"]["query"] == "What are Q3 supply risks?"
    assert memory.calls[0]["kwargs"]["metadata"]["human_gate_status"] == "approved"
    assert output["human_override_rate"] == 0.0
    approval_events = [event for event in output["audit_trail"] if event.event_type == "human_gate.approved"]
    assert approval_events[0].approved_by == "board-chair"
    assert approval_events[0].payload["rationale"] == "Sources reviewed"
    assert approval_events[0].created_at is not None


def test_rejection_resume_logs_audit_and_skips_memory_store(monkeypatch) -> None:
    configure_interrupt_mode(monkeypatch)
    memory = FakeBriefMemory()
    graph = build_graph(FakeRetriever(), checkpointer=MemorySaver(), episodic_memory=memory)
    config = {"configurable": {"thread_id": "run-reject"}}
    graph.invoke(initial_state("What are Q3 supply risks?", run_id="run-reject", session_id="session-reject"), config=config)

    output = graph.invoke(
        Command(resume={"status": "rejected", "approver_id": "cfo", "rationale": "Needs newer source"}),
        config=config,
    )

    assert output["human_approved"] is False
    assert output["brief_stored"] is False
    assert memory.calls == []
    assert output["human_override_rate"] == 1.0
    rejection_events = [event for event in output["audit_trail"] if event.event_type == "human_gate.rejected"]
    assert rejection_events[0].approved_by == "cfo"
    assert rejection_events[0].payload["rationale"] == "Needs newer source"
