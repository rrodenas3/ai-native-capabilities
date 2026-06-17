from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from core.schemas import AgentHop, AuditEvent
from core.utils.settings import get_settings

MODULE_PATH = Path(__file__).parents[1] / "agents" / "supervisor.py"
SPEC = importlib.util.spec_from_file_location("cap01_supervisor", MODULE_PATH)
assert SPEC and SPEC.loader
supervisor_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = supervisor_module
SPEC.loader.exec_module(supervisor_module)

supervisor_node = supervisor_module.supervisor_node


def base_state(query: str, **overrides):
    state = {
        "run_id": "run-1",
        "session_id": "session-1",
        "capability_id": "cap-01",
        "query": query,
        "messages": [],
        "current_agent": "",
        "agent_hops": [],
        "audit_trail": [],
    }
    state.update(overrides)
    return state


def test_supervisor_decomposes_query_and_logs(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    result = supervisor_node(base_state("What are supply risks and margin opportunities?"))

    assert result["sub_queries"] == ["What are supply risks", "margin opportunities"]
    assert result["next_agents"] == ["retrieval"]
    assert isinstance(result["agent_hops"][0], AgentHop)
    assert result["agent_hops"][0].model == "claude-sonnet-4-6"
    assert isinstance(result["audit_trail"][0], AuditEvent)


def test_supervisor_routes_web_research_only_below_threshold(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    high = supervisor_node(base_state("Internal board strategy", corpus_confidence=0.31))
    low = supervisor_node(base_state("Internal board strategy", corpus_confidence=0.29))

    assert high["next_agents"] == ["retrieval"]
    assert low["next_agents"] == ["retrieval", "web_research"]


def test_supervisor_sets_corpus_scope(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    result = supervisor_node(base_state("Board strategy revenue and market risks"))

    assert "internal-knowledge-base" in result["corpus_scope"]
    assert "board-documents" in result["corpus_scope"]
    assert "financial-reports" in result["corpus_scope"]
    assert "market-research" in result["corpus_scope"]


def test_supervisor_preserves_existing_corpus_scope(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()

    result = supervisor_node(base_state("Any question", corpus_scope=["custom"]))

    assert result["corpus_scope"] == ["custom"]


def test_supervisor_handles_20_diverse_queries(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
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
        "Compare product risk and customer risk",
        "What should leadership know about churn?",
        "Where do we have supplier concentration?",
        "What internal evidence supports the strategy?",
        "Assess legal risk and financial exposure",
        "Which initiatives have weak KPIs?",
        "What does research say about onboarding?",
        "Find contradictions in board updates",
        "What are the top risks, opportunities, and unknowns?",
        "Which follow-up actions should we take?",
    ]

    results = [supervisor_node(base_state(query)) for query in queries]

    assert all(result["sub_queries"] for result in results)
    assert all("internal-knowledge-base" in result["corpus_scope"] for result in results)

