"""Tests for unified eval gate configuration."""

from __future__ import annotations

from core.evals.gate_config import (
    BLOCKING_METRICS,
    ENFORCED_CAPS,
    evaluate_report,
    is_enforced_cap,
)


def test_all_enforced_caps_have_blocking_metrics() -> None:
    for cap_id in ENFORCED_CAPS:
        assert cap_id in BLOCKING_METRICS
        assert len(BLOCKING_METRICS[cap_id]) >= 2


def test_missing_eval_suite_fails_enforced_cap() -> None:
    report = {"cap": "cap-01", "status": "no_eval_suite", "metrics": {}}
    result = evaluate_report(report, "cap-01")
    assert not result.passed
    assert result.fatal_status == "no_eval_suite"


def test_passing_cap01_metrics() -> None:
    report = {
        "cap": "cap-01",
        "status": "ok",
        "metrics": {
            "citation_accuracy": 0.96,
            "hallucination_rate": 0.01,
        },
    }
    result = evaluate_report(report, "cap-01")
    assert result.passed
    assert result.failures == []


def test_failing_hallucination_rate() -> None:
    report = {
        "cap": "cap-01",
        "status": "ok",
        "metrics": {
            "citation_accuracy": 0.99,
            "hallucination_rate": 0.05,
        },
    }
    result = evaluate_report(report, "cap-01")
    assert not result.passed
    assert any(name == "hallucination_rate" for name, _, _, _ in result.failures)


def test_is_enforced_cap() -> None:
    assert is_enforced_cap("cap-03")
    assert not is_enforced_cap("cap-99")
