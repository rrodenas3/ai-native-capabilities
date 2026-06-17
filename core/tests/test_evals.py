from __future__ import annotations

import json

from core.evals import COMMON_METRICS, AgentResult, EvalSuite, TestCase


def test_common_metric_names_are_complete() -> None:
    assert COMMON_METRICS == [
        "task_success_rate",
        "human_override_rate",
        "cost_per_task_usd",
        "response_latency_p95_ms",
        "hallucination_rate",
    ]


def test_run_common_computes_shared_metrics(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "real")
    suite = EvalSuite()
    results = [
        AgentResult(success=True, cost_usd=0.1, latency_ms=100.0, grounded=True),
        AgentResult(
            success=False,
            human_overridden=True,
            cost_usd=0.3,
            latency_ms=500.0,
            grounded=False,
        ),
    ]

    metrics = suite.run_common(results)

    assert metrics.task_success_rate == 0.5
    assert metrics.human_override_rate == 0.5
    assert metrics.cost_per_task_usd == 0.2
    assert metrics.response_latency_p95_ms == 500.0
    assert metrics.hallucination_rate == 0.5


def test_hallucination_rate_is_zero_in_mock_mode_without_judge(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    suite = EvalSuite()

    metrics = suite.run_common([AgentResult(success=True, grounded=False)])

    assert metrics.hallucination_rate == 0.0


def test_hallucination_judge_can_be_injected(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "real")
    suite = EvalSuite(hallucination_judge=lambda result: "unsupported" in result.output)

    metrics = suite.run_common(
        [
            AgentResult(success=True, output="supported"),
            AgentResult(success=True, output="unsupported claim"),
        ]
    )

    assert metrics.hallucination_rate == 0.5


def test_run_returns_valid_eval_report_json(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    suite = EvalSuite()

    report = suite.run(
        "cap-01",
        [
            TestCase("case-1", AgentResult(success=True, cost_usd=0.1, latency_ms=100.0)),
            TestCase("case-2", AgentResult(success=True, cost_usd=0.2, latency_ms=200.0)),
        ],
    )
    payload = json.loads(report.model_dump_json())

    assert payload["cap"] == "cap-01"
    assert payload["status"] == "pass"
    assert payload["metrics"]["task_success_rate"] == 1.0
    assert payload["blocking_failures"] == []


def test_check_gates_identifies_blocking_failures(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "real")
    suite = EvalSuite()
    report = suite.run(
        "cap-01",
        [
            TestCase("case-1", AgentResult(success=False, grounded=False)),
            TestCase("case-2", AgentResult(success=False, grounded=False)),
        ],
    )

    gate = suite.check_gates(report)

    assert gate.passed is False
    assert "task_success_rate" in report.blocking_failures
    assert "hallucination_rate" in report.blocking_failures
    assert gate.criteria_results["human_override_rate"] is True


def test_capability_specific_metrics_are_included(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    suite = EvalSuite(capability_eval_fn=lambda cap, results: {"citation_accuracy": 0.97})

    report = suite.run("cap-01", [TestCase("case-1", AgentResult(success=True))])

    assert report.metrics["citation_accuracy"] == 0.97
    assert any(metric.name == "citation_accuracy" for metric in report.metric_results)

