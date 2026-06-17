from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from core.schemas import AgentHop, AuditEvent, CapabilityID, DocumentChunk, RetrievalResult
from core.utils.settings import get_settings

MODULE_PATH = Path(__file__).parents[1] / "agents" / "verification_agent.py"
SPEC = importlib.util.spec_from_file_location("cap01_verification_agent", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

verification_agent_node = module.verification_agent_node
VerificationFlag = module.VerificationFlag


def result(content: str) -> RetrievalResult:
    return RetrievalResult(
        chunk=DocumentChunk(
            capability=CapabilityID.DECISION_INTELLIGENCE,
            doc_id="doc-1",
            chunk_index=0,
            content=content,
        ),
        semantic_score=1.0,
        lexical_score=None,
        combined_score=1.0,
        rank=1,
    )


def base_state(**overrides):
    state = {
        "run_id": "run-1",
        "session_id": "session-1",
        "analysis_notes": "Supply risk will increase due to supplier concentration.",
        "retrieval_results": [result("Supply risk will increase due to supplier concentration.")],
        "uncertainty_flags": [],
        "agent_hops": [],
        "audit_trail": [],
    }
    state.update(overrides)
    return state


def test_verification_agent_supports_grounded_claim(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = verification_agent_node(base_state())

    assert output["verification_flags"] == []
    assert output["citation_accuracy"] == 1.0


def test_verification_agent_flags_unverified_claim(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = verification_agent_node(
        base_state(
            analysis_notes="Regulatory exposure will decline next quarter.",
            retrieval_results=[result("Supply risk will increase due to supplier concentration.")],
        )
    )

    assert len(output["verification_flags"]) == 1
    assert isinstance(output["verification_flags"][0], VerificationFlag)
    assert output["verification_flags"][0].status == "UNVERIFIED"
    assert "UNVERIFIED:" in output["uncertainty_flags"][0]


def test_verification_agent_never_removes_analysis_notes(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    notes = "Unsupported claim appears here."

    output = verification_agent_node(base_state(analysis_notes=notes, retrieval_results=[]))

    assert output["analysis_notes"] == notes


def test_verification_agent_logs_hop_and_audit(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = verification_agent_node(base_state())

    assert isinstance(output["agent_hops"][0], AgentHop)
    assert output["agent_hops"][0].model == "claude-opus-4-8"
    assert isinstance(output["audit_trail"][0], AuditEvent)
    assert output["audit_trail"][0].event_type == "verification.completed"

