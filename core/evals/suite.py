"""Common EvalSuite implementation."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from uuid import uuid4

from core.evals.metrics import (
    COMMON_METRICS,
    AgentResult,
    CommonMetrics,
    HallucinationJudge,
    TestCase,
    compute_common_metrics,
)
from core.schemas.base import EvalReport, GateResult, MetricResult

MetricThreshold = tuple[float, bool, bool]  # threshold, lower_is_better, blocking

DEFAULT_THRESHOLDS: dict[str, MetricThreshold] = {
    "task_success_rate": (0.85, False, True),
    "human_override_rate": (0.15, True, False),
    "cost_per_task_usd": (1.00, True, False),
    "response_latency_p95_ms": (30_000.0, True, False),
    "hallucination_rate": (0.02, True, True),
}


class EvalSuite:
    """Run common and capability-specific evals."""

    def __init__(
        self,
        *,
        thresholds: dict[str, MetricThreshold] | None = None,
        hallucination_judge: HallucinationJudge | None = None,
        capability_eval_fn: Callable[[str, list[AgentResult]], dict[str, float]] | None = None,
    ) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.hallucination_judge = hallucination_judge
        self.capability_eval_fn = capability_eval_fn

    def run(self, capability_id: str, test_set: list[TestCase]) -> EvalReport:
        started = perf_counter()
        results = [case.result for case in test_set]
        common = self.run_common(results)
        capability_metrics = self.run_capability_specific(capability_id, results)
        metrics = {**common.model_dump(), **capability_metrics}
        metric_results = [self._metric_result(name, value) for name, value in metrics.items()]
        blocking_failures = [
            metric.name for metric in metric_results if metric.blocking and not metric.passed
        ]
        score = _weighted_score(metric_results)
        status = "fail" if blocking_failures else "pass" if score >= 0.85 else "warn"
        return EvalReport(
            cap=capability_id,
            status=status,
            score=score,
            metrics=metrics,
            metric_results=metric_results,
            blocking_failures=blocking_failures,
            total_cost_usd=sum(result.cost_usd for result in results),
            elapsed_s=round(perf_counter() - started, 3),
            run_id=str(uuid4()),
        )

    def run_common(self, results: list[AgentResult]) -> CommonMetrics:
        return compute_common_metrics(results, self.hallucination_judge)

    def run_capability_specific(
        self,
        capability_id: str,
        results: list[AgentResult],
    ) -> dict[str, float]:
        if self.capability_eval_fn is None:
            return {}
        return self.capability_eval_fn(capability_id, results)

    def check_gates(self, report: EvalReport) -> GateResult:
        criteria = {metric.name: metric.passed for metric in report.metric_results}
        blocking_passed = not report.blocking_failures
        return GateResult(
            gate_number=4,
            gate_name="quality",
            passed=blocking_passed,
            criteria_results=criteria,
            notes=None if blocking_passed else ", ".join(report.blocking_failures),
        )

    def _metric_result(self, name: str, value: float) -> MetricResult:
        threshold, lower_is_better, blocking = self.thresholds.get(name, (0.0, False, False))
        passed = value <= threshold if lower_is_better else value >= threshold
        return MetricResult(
            name=name,
            value=value,
            threshold=threshold,
            lower_is_better=lower_is_better,
            passed=passed,
            blocking=blocking,
        )


def _weighted_score(metric_results: list[MetricResult]) -> float:
    if not metric_results:
        return 0.0
    return sum(metric.passed for metric in metric_results) / len(metric_results)


def common_metric_names() -> list[str]:
    return list(COMMON_METRICS)

