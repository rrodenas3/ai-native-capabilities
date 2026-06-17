from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.schemas import AgentHop, AuditEvent, CapabilityID, Citation, DocumentChunk, Finding, RetrievalResult
from core.utils.settings import get_settings

AGENT_PATH = Path(__file__).parents[1] / "agents" / "brief_agent.py"
AGENT_SPEC = importlib.util.spec_from_file_location("cap01_brief_agent", AGENT_PATH)
if AGENT_SPEC is None or AGENT_SPEC.loader is None:
    raise RuntimeError(f"Unable to load brief agent module from {AGENT_PATH}")
agent_module = importlib.util.module_from_spec(AGENT_SPEC)
sys.modules[AGENT_SPEC.name] = agent_module
AGENT_SPEC.loader.exec_module(agent_module)

SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "brief.py"
schema_module = sys.modules.get("cap01_brief_schema")
if schema_module is None:
    SCHEMA_SPEC = importlib.util.spec_from_file_location("cap01_brief_schema", SCHEMA_PATH)
    if SCHEMA_SPEC is None or SCHEMA_SPEC.loader is None:
        raise RuntimeError(f"Unable to load brief schema from {SCHEMA_PATH}")
    schema_module = importlib.util.module_from_spec(SCHEMA_SPEC)
    sys.modules[SCHEMA_SPEC.name] = schema_module
    SCHEMA_SPEC.loader.exec_module(schema_module)

brief_agent_node = agent_module.brief_agent_node
BriefOutput = schema_module.BriefOutput


def result(doc_id: str, content: str, score: float = 0.82, *, title: str = "Strategy Memo") -> RetrievalResult:
    return RetrievalResult(
        chunk=DocumentChunk(
            capability=CapabilityID.DECISION_INTELLIGENCE,
            doc_id=doc_id,
            chunk_index=0,
            content=content,
            metadata={"title": title, "date": "2026-06-01"},
            access_tier="internal",
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
        "query": "What are our supply chain risks entering Q3?",
        "analysis_notes": "\n".join(
            [
                "Key themes: supplier concentration, margin pressure",
                "Evidence strength: 0.820",
                "Gaps: competitor mitigation evidence",
                "Contradictions: none detected",
            ]
        ),
        "key_themes": ["supplier concentration", "margin pressure"],
        "retrieval_results": [
            result(
                "doc-a",
                "Supplier concentration increases Q3 supply chain risk and may pressure margins.",
                0.9,
                title="Q3 Supply Chain Memo",
            ),
            result("doc-b", "Margin pressure is elevated because expedited logistics costs remain high.", 0.74),
        ],
        "uncertainty_flags": ["competitor mitigation evidence is missing"],
        "verification_flags": [],
        "evidence_strength": 0.82,
        "citation_accuracy": 1.0,
        "agent_hops": [],
        "audit_trail": [],
    }
    state.update(overrides)
    return state


def test_brief_agent_outputs_exact_schema_and_grounded_findings(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = brief_agent_node(base_state())

    brief = output["brief"]
    assert isinstance(brief, BriefOutput)
    assert output["executive_summary"] == brief.executive_summary
    assert output["key_findings"] == brief.key_findings
    assert 0.0 <= output["overall_confidence"] <= 1.0
    assert all(isinstance(finding, Finding) for finding in brief.key_findings)
    assert all(finding.citations for finding in brief.key_findings)
    assert all(isinstance(finding.citations[0], Citation) for finding in brief.key_findings)


def test_overall_confidence_is_average_of_finding_confidences(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = brief_agent_node(base_state())
    findings = output["key_findings"]
    expected = round(sum(finding.confidence for finding in findings) / len(findings), 3)

    assert output["overall_confidence"] == expected


def test_uncertainty_flags_are_prominent_and_actions_are_concrete(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = brief_agent_node(base_state())

    assert output["uncertainty_flags"] == ["competitor mitigation evidence is missing"]
    assert "uncertainties" in output["executive_summary"]
    assert 3 <= len(output["recommended_actions"]) <= 5
    assert any("uncertainty flags" in action.lower() for action in output["recommended_actions"])


def test_brief_text_has_no_raw_retrieval_artifacts(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = brief_agent_node(base_state())
    visible_text = " ".join(
        [
            output["executive_summary"],
            *[finding.claim for finding in output["key_findings"]],
            *output["recommended_actions"],
        ]
    ).lower()

    assert "retrievalresult" not in visible_text
    assert "chunk_index" not in visible_text
    assert "semantic_score" not in visible_text
    assert "agent" not in output["executive_summary"].lower()


def test_brief_schema_rejects_findings_without_citations() -> None:
    with pytest.raises(ValidationError, match="Every finding must include at least one citation"):
        BriefOutput(
            executive_summary="Summary.",
            key_findings=[Finding(claim="Unsupported claim.", citations=[], confidence=0.2)],
            uncertainty_flags=["Missing source."],
            recommended_actions=["Review sources.", "Gather evidence.", "Escalate for review."],
            overall_confidence=0.2,
        )


def test_brief_agent_logs_hop_and_audit(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    output = brief_agent_node(base_state())

    assert isinstance(output["agent_hops"][0], AgentHop)
    assert output["agent_hops"][0].model == "claude-opus-4-8"
    assert output["agent_hops"][0].confidence == output["overall_confidence"]
    assert isinstance(output["audit_trail"][0], AuditEvent)
    assert output["audit_trail"][0].event_type == "brief.completed"
