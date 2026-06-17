from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from core.schemas import AgentHop, AuditEvent, CapabilityID, DocumentChunk, RetrievalResult
from core.utils.settings import get_settings

MODULE_PATH = Path(__file__).parents[1] / "agents" / "analysis_agent.py"
SPEC = importlib.util.spec_from_file_location("cap01_analysis_agent", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load analysis agent module from {MODULE_PATH}")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

analysis_agent_node = module.analysis_agent_node


def result(doc_id: str, content: str, score: float = 0.8) -> RetrievalResult:
    return RetrievalResult(
        chunk=DocumentChunk(
            capability=CapabilityID.DECISION_INTELLIGENCE,
            doc_id=doc_id,
            chunk_index=0,
            content=content,
        ),
        semantic_score=score,
        lexical_score=None,
        combined_score=score,
        rank=1,
    )


def base_state(**overrides):
    state = {
        "run_id": "run-1",
        "session_id": "session-1",
        "sub_queries": ["supply risk", "pricing pressure"],
        "retrieval_results": [
            result("doc-a", "Supply risk will increase due to supplier concentration."),
            result("doc-b", "Pricing pressure may decrease margin."),
        ],
        "agent_hops": [],
        "audit_trail": [],
    }
    state.update(overrides)
    return state


def test_analysis_agent_structures_notes(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = analysis_agent_node(base_state())

    assert "Key themes:" in output["analysis_notes"]
    assert "Evidence strength:" in output["analysis_notes"]
    assert "Gaps:" in output["analysis_notes"]
    assert "Contradictions:" in output["analysis_notes"]


def test_analysis_agent_detects_contradictions(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    state = base_state(
        retrieval_results=[
            result("doc-a", "Supply risk will increase."),
            result("doc-b", "Supply risk will decrease."),
        ]
    )

    output = analysis_agent_node(state)

    assert output["contradictions"]


def test_analysis_agent_ignores_single_document_with_opposing_terms(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    state = base_state(
        retrieval_results=[result("doc-a", "Supply risk may increase in Q1 and decrease in Q2.")]
    )

    output = analysis_agent_node(state)

    assert output["contradictions"] == []


def test_analysis_agent_detects_gaps(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    state = base_state(sub_queries=["regulatory exposure"], retrieval_results=[result("doc-a", "Supply risk")])

    output = analysis_agent_node(state)

    assert output["uncertainty_flags"] == ["No retrieved evidence covers: regulatory exposure"]


def test_analysis_agent_gap_detection_includes_short_business_terms(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    state = base_state(sub_queries=["risk cost ROI NPV"], retrieval_results=[result("doc-a", "unrelated evidence")])

    output = analysis_agent_node(state)

    assert output["uncertainty_flags"] == ["No retrieved evidence covers: risk cost ROI NPV"]


def test_analysis_agent_uses_powerful_model_and_logs(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = analysis_agent_node(base_state())

    assert isinstance(output["agent_hops"][0], AgentHop)
    assert output["agent_hops"][0].model == "claude-opus-4-8"
    assert isinstance(output["audit_trail"][0], AuditEvent)
    assert output["audit_trail"][0].event_type == "analysis.completed"


def test_analysis_agent_does_not_invent_when_no_results(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = analysis_agent_node(base_state(retrieval_results=[]))

    assert "none from retrieved evidence" in output["analysis_notes"]
    assert "No retrieved evidence available for analysis" in output["uncertainty_flags"]

