from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from core.utils.settings import get_settings

ROOT = Path(__file__).parents[1]


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


schema = load("schemas/briefing_script.py", "cap02_schema_agent_test")
execution = load("agents/execution_agent.py", "cap02_execution_test")
mentor = load("agents/mentor_agent.py", "cap02_mentor_test")
security = load("tools/security_gate.py", "cap02_security_agent_test")
mrp = load("agents/mrp_agent.py", "cap02_mrp_test")
graph_module = load("agents/graph.py", "cap02_graph_test")


def test_execution_mentor_security_and_mrp_pipeline(tmp_path) -> None:
    briefing = schema.minimal_valid_briefing()
    state = execution.execution_agent_node({"briefing": briefing, "git_branch": "feature/work"})
    state = mentor.mentor_review_node(state)
    state = security.security_gate_node({**state, "security_scan_root": tmp_path})
    state = mrp.mrp_agent_node(state)

    assert state["merge_readiness_pack"].ready is True
    assert state["human_review_artifact"] == state["merge_readiness_pack"]
    assert len(state["merge_readiness_pack"].criteria_scores) == len(briefing.what_and_success.acceptance_criteria)


def test_execution_on_main_raises_crp() -> None:
    briefing = schema.minimal_valid_briefing()

    state = execution.execution_agent_node({"briefing": briefing, "git_branch": "main", "crps_raised": []})

    assert state["status"] == "CRP_PENDING"
    assert state["crps_raised"][0].proposed_solution


def test_mentor_flags_trivial_tests() -> None:
    briefing = schema.minimal_valid_briefing()
    state = mentor.mentor_review_node(
        {
            "briefing": briefing,
            "output_files": {"tests/test_bad.py": "def test_bad():\n    assert True\n"},
            "test_results": {"passed": True},
        }
    )

    assert state["criteria_scores"][0].status == schema.CriteriaStatus.PARTIAL
    assert state["test_quality_issues"]


def test_graph_blocks_invalid_brief_before_execution() -> None:
    graph = graph_module.build_graph(checkpointer=MemorySaver())

    output = graph.invoke(
        graph_module.initial_state(run_id="run-invalid", session_id="session-invalid", briefing_data={}),
        config={"configurable": {"thread_id": "run-invalid"}},
    )

    assert output["status"] == "INVALID_BRIEFING"
    assert "files_changed" not in output


def test_graph_valid_brief_reaches_human_approval(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("EVAL_MODE", "ci")
    monkeypatch.setenv("HUMAN_GATE_MOCK_APPROVED", "true")
    get_settings.cache_clear()
    briefing = schema.minimal_valid_briefing().model_dump(mode="json")
    graph = graph_module.build_graph(checkpointer=MemorySaver())

    output = graph.invoke(
        graph_module.initial_state(run_id="run-valid", session_id="session-valid", briefing_data=briefing),
        config={"configurable": {"thread_id": "run-valid"}},
    )

    assert output["human_approved"] is True
    assert output["merge_readiness_pack"].ready is True
    assert output["human_review_artifact"] == output["merge_readiness_pack"]


def test_graph_crp_interrupt_and_resume(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.delenv("EVAL_MODE", raising=False)
    monkeypatch.delenv("HUMAN_GATE_MOCK_APPROVED", raising=False)
    get_settings.cache_clear()
    briefing = schema.minimal_valid_briefing().model_dump(mode="json")
    graph = graph_module.build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "run-crp"}}
    state = graph_module.initial_state(run_id="run-crp", session_id="session-crp", briefing_data=briefing)
    state["git_branch"] = "main"

    paused = graph.invoke(state, config=config)
    resumed = graph.invoke(Command(resume={"status": "resolved", "decision": "use feature branch"}), config=config)

    assert "__interrupt__" in paused
    assert resumed["crps_resolved"]
    assert resumed["status"] in {"MRP_READY", "CRP_RESOLVED"}
