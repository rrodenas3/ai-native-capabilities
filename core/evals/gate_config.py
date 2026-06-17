"""Single source of truth for capability eval gate thresholds."""

from __future__ import annotations

from dataclasses import dataclass, field

# Capabilities with eval suites that must pass in CI (see README roadmap).
ENFORCED_CAPS: tuple[str, ...] = (
    "cap-01",
    "cap-02",
    "cap-03",
    "cap-04",
    "cap-05",
)

# (metric_name, threshold, lower_is_better)
MetricGate = tuple[str, float, bool]

# Derived from each capability SPEC.md eval_scorecard blocking fields.
BLOCKING_METRICS: dict[str, list[MetricGate]] = {
    "cap-01": [
        ("citation_accuracy", 0.95, False),
        ("hallucination_rate", 0.02, True),
    ],
    "cap-02": [
        ("briefing_completeness", 1.00, False),
        ("security_weakness_rate", 5.0, True),
    ],
    "cap-03": [
        ("agent_sprawl_count", 2.0, True),
        ("escalation_accuracy", 0.90, False),
    ],
    "cap-04": [
        ("human_approval_coverage", 1.00, False),
        ("digital_twin_validation", 1.00, False),
    ],
    "cap-05": [
        ("false_negative_rate_obligations", 0.01, True),
        ("citation_accuracy", 0.98, False),
        ("expert_review_coverage", 1.00, False),
        ("query_answer_citation_rate", 1.00, False),
    ],
}

WARNING_THRESHOLDS: dict[str, list[MetricGate]] = {
    "cap-01": [
        ("retrieval_recall", 0.85, False),
        ("human_override_rate", 0.15, True),
        ("response_latency_p95_s", 30.0, True),
        ("cost_per_brief_usd", 0.50, True),
    ],
    "cap-02": [
        ("acceptance_criteria_pass", 0.90, False),
        ("test_coverage", 0.80, False),
        ("cost_per_task_usd", 2.00, True),
    ],
    "cap-03": [
        ("intent_classification_accuracy", 0.92, False),
        ("basket_margin_awareness", 0.95, False),
        ("response_latency_p95_ms", 1500.0, True),
    ],
    "cap-04": [
        ("forecast_accuracy_mape", 0.15, True),
        ("stockout_reduction_rate", 0.30, False),
        ("autonomous_action_accuracy", 0.95, False),
        ("exception_detection_recall", 0.90, False),
    ],
    "cap-05": [
        ("false_positive_rate_obligations", 0.10, True),
        ("gap_detection_accuracy", 0.90, False),
        ("knowledge_graph_accuracy", 0.92, False),
    ],
}

_FATAL_STATUSES = frozenset({"no_eval_suite", "not_found", "error"})


@dataclass
class GateEvaluation:
    cap_id: str
    passed: bool
    failures: list[tuple[str, float, float, bool]] = field(default_factory=list)
    warnings: list[tuple[str, float, float, bool]] = field(default_factory=list)
    fatal_status: str | None = None
    fatal_note: str | None = None

    @property
    def failure_names(self) -> list[str]:
        if self.fatal_status:
            return [self.fatal_status]
        return [name for name, _, _, _ in self.failures]


def is_enforced_cap(cap_id: str) -> bool:
    return cap_id in ENFORCED_CAPS


def check_metric(value: float, threshold: float, lower_is_better: bool) -> bool:
    if lower_is_better:
        return value <= threshold
    return value >= threshold


def evaluate_report(report: dict, cap_id: str) -> GateEvaluation:
    """Evaluate blocking and warning metrics for a cap eval report dict."""
    status = report.get("status", "unknown")
    if status in _FATAL_STATUSES:
        note = report.get("note") or report.get("stderr") or ""
        if is_enforced_cap(cap_id):
            return GateEvaluation(
                cap_id=cap_id,
                passed=False,
                fatal_status=status,
                fatal_note=str(note) if note else None,
            )
        return GateEvaluation(cap_id=cap_id, passed=True, fatal_status=status)

    metrics = report.get("metrics", {})
    blocking = BLOCKING_METRICS.get(cap_id, [])
    warnings = WARNING_THRESHOLDS.get(cap_id, [])

    failures: list[tuple[str, float, float, bool]] = []
    warns: list[tuple[str, float, float, bool]] = []

    for metric_name, threshold, lower_is_better in blocking:
        if metric_name not in metrics:
            failures.append((metric_name, -1.0, threshold, lower_is_better))
            continue
        value = float(metrics[metric_name])
        if not check_metric(value, threshold, lower_is_better):
            failures.append((metric_name, value, threshold, lower_is_better))

    for metric_name, threshold, lower_is_better in warnings:
        if metric_name not in metrics:
            continue
        value = float(metrics[metric_name])
        if not check_metric(value, threshold, lower_is_better):
            warns.append((metric_name, value, threshold, lower_is_better))

    return GateEvaluation(
        cap_id=cap_id,
        passed=len(failures) == 0,
        failures=failures,
        warnings=warns,
    )
