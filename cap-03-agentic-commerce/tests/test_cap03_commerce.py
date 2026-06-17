from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


intent = load("agents/intent_classifier.py", "cap03_intent_test")
discovery = load("agents/discovery_agent.py", "cap03_discovery_test")
support = load("agents/support_agent.py", "cap03_support_test")
sentiment = load("tools/sentiment.py", "cap03_sentiment_test")
escalation = load("agents/escalation_agent.py", "cap03_escalation_test")
session_store = load("memory/session_store.py", "cap03_session_test")
sparky = load("agents/sparky_graph.py", "cap03_sparky_test")
eval_suite = load("evals/suite.py", "cap03_eval_test")


def test_intent_classifier_exceeds_fixture_target() -> None:
    cases = json.loads((ROOT / "tests" / "fixtures" / "intent_test_set.json").read_text(encoding="utf-8"))

    accuracy = sum(intent.classify_intent(case["query"]).intent_class.value == case["intent"] for case in cases) / len(cases)

    assert len(cases) == 500
    assert accuracy >= 0.92
    assert intent.classify_intent("hmm").intent_class.value == "CLARIFICATION"


def test_discovery_recommendations_are_relevant_in_stock_and_margin_safe() -> None:
    state = discovery.discovery_node({"raw_message": "need coffee espresso gift"})

    recommendations = state["recommendations"]
    assert any("coffee" in rec.product.tags for rec in recommendations[:3])
    assert recommendations[0].margin_score >= 0
    assert recommendations[0].stock_score == 1.0


def test_support_uses_live_order_data_and_policy_citation() -> None:
    state = support.support_node({"raw_message": "Can I return order 1001?"})

    assert state["resolution"].order_id == "1001"
    assert state["resolution"].citations == ["Policy RETURNS-01"]
    assert "Live OMS status" in state["resolution"].resolution_text


def test_sentiment_detects_frustration_conservatively() -> None:
    labelled = [
        "I am furious and want a human now",
        "THIS IS UNACCEPTABLE",
        "This is the third time I have asked",
        "Get me a manager",
        "I will never buy here again",
    ]

    assert sum(sentiment.detect_sentiment(message).frustration_flag for message in labelled) / len(labelled) >= 0.90


def test_escalation_rules_cover_mandatory_cases() -> None:
    assert escalation.should_escalate({"frustration_flag": True}).escalation_triggered is True
    assert escalation.should_escalate({"raw_message": "payment dispute on my card"}).escalation_triggered is True
    assert escalation.should_escalate({"intent_class": "COMPLAINT"}).escalation_triggered is True


def test_session_memory_is_opt_in_and_ttl_governed() -> None:
    store = session_store.SessionStore(ttl_days=30)

    assert store.store_session("s1", opt_in=False, customer_id="cust-1") is None
    stored = store.store_session("s1", opt_in=True, customer_id="cust-1", preferences={"category": "coffee"})

    assert stored is not None
    assert store.retrieve_session("s1").preferences["category"] == "coffee"


def test_sparky_graph_routes_discovery_support_and_escalation() -> None:
    graph = sparky.build_graph(checkpointer=MemorySaver())

    discovery_output = graph.invoke(
        sparky.initial_state("I need a coffee gift recommendation", session_id="g1"),
        config={"configurable": {"thread_id": "g1"}},
    )
    support_output = graph.invoke(
        sparky.initial_state("Where is order 1001?", session_id="g2"),
        config={"configurable": {"thread_id": "g2"}},
    )
    escalation_output = graph.invoke(
        sparky.initial_state("I am furious and want a human now", session_id="g3"),
        config={"configurable": {"thread_id": "g3"}},
    )

    assert discovery_output["recommendations"]
    assert support_output["resolution"].order_id == "1001"
    assert escalation_output["escalation_triggered"] is True
    assert discovery_output["agent_type"] == "sparky"


def test_eval_suite_passes_blocking_metrics() -> None:
    report = eval_suite.run_eval()

    assert report["status"] == "pass"
    assert report["metrics"]["agent_sprawl_count"] <= 2
    assert report["metrics"]["escalation_accuracy"] >= 0.90
