#!/usr/bin/env python3
"""Cap-01 evaluation suite."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import mean
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from core.schemas import EvalReport, MetricResult  # noqa: E402

CAPABILITY_ID = "cap-01"
FIXTURE_PATH = ROOT / "cap-01-decision-intelligence" / "tests" / "fixtures" / "cap01_eval_cases.json"

THRESHOLDS: dict[str, tuple[float, bool, bool, float]] = {
    "citation_accuracy": (0.95, False, True, 0.25),
    "hallucination_rate": (0.02, True, True, 0.25),
    "retrieval_recall": (0.85, False, False, 0.20),
    "source_coverage": (0.80, False, False, 0.10),
    "response_latency_p95_s": (30.0, True, False, 0.05),
    "human_override_rate": (0.15, True, False, 0.05),
    "brief_usefulness": (4.0, False, False, 0.05),
    "cost_per_brief_usd": (0.50, True, False, 0.05),
}


def run_eval(fixture_path: Path = FIXTURE_PATH) -> EvalReport:
    started = perf_counter()
    cases = _load_cases(fixture_path)
    metrics = {
        "citation_accuracy": citation_accuracy(cases),
        "hallucination_rate": hallucination_rate(cases),
        "retrieval_recall": retrieval_recall(cases),
        "source_coverage": source_coverage(cases),
        "response_latency_p95_s": response_latency_p95_s(cases),
        "human_override_rate": human_override_rate(cases),
        "brief_usefulness": brief_usefulness(cases),
        "cost_per_brief_usd": cost_per_brief_usd(cases),
    }
    metric_results = [_metric_result(name, value) for name, value in metrics.items()]
    blocking_failures = [metric.name for metric in metric_results if metric.blocking and not metric.passed]
    score = _weighted_score(metric_results)
    status = "fail" if blocking_failures else "pass" if score >= 0.85 else "warn"
    return EvalReport(
        cap=CAPABILITY_ID,
        status=status,
        score=score,
        metrics=metrics,
        metric_results=metric_results,
        blocking_failures=blocking_failures,
        total_cost_usd=round(sum(float(case.get("cost_usd", 0.0)) for case in cases), 6),
        elapsed_s=round(perf_counter() - started, 3),
        run_id=str(uuid4()),
    )


def citation_accuracy(cases: list[dict]) -> float:
    total = 0
    matched = 0
    for case in cases:
        retrieval_text_by_doc = {
            str(item["doc_id"]): str(item["content"]).lower()
            for item in case.get("retrieval_results", [])
        }
        for finding in case.get("brief", {}).get("key_findings", []):
            citations = finding.get("citations", [])
            for citation in citations:
                total += 1
                source_text = retrieval_text_by_doc.get(str(citation.get("source_doc_id")), "")
                excerpt = str(citation.get("excerpt", "")).lower()
                if excerpt and excerpt in source_text:
                    matched += 1
    return round(matched / total, 4) if total else 0.0


def hallucination_rate(cases: list[dict]) -> float:
    if os.getenv("LLM_MODE", "mock") == "mock":
        return 0.0
    ungrounded = 0
    for case in cases:
        retrieval_text = " ".join(str(item["content"]).lower() for item in case.get("retrieval_results", []))
        for finding in case.get("brief", {}).get("key_findings", []):
            claim_terms = _terms(str(finding.get("claim", "")))
            if claim_terms and len(claim_terms & _terms(retrieval_text)) / len(claim_terms) < 0.4:
                ungrounded += 1
    total_findings = sum(len(case.get("brief", {}).get("key_findings", [])) for case in cases)
    return round(ungrounded / total_findings, 4) if total_findings else 0.0


def retrieval_recall(cases: list[dict]) -> float:
    recalls = []
    for case in cases:
        expected = set(case.get("relevant_doc_ids", []))
        retrieved = {item["doc_id"] for item in case.get("retrieval_results", [])}
        if expected:
            recalls.append(len(expected & retrieved) / len(expected))
    return round(mean(recalls), 4) if recalls else 0.0


def source_coverage(cases: list[dict]) -> float:
    values = []
    for case in cases:
        corpus_count = int(case.get("corpus_doc_count", 0))
        indexed_count = int(case.get("indexed_doc_count", 0))
        if corpus_count > 0:
            values.append(indexed_count / corpus_count)
    return round(mean(values), 4) if values else 0.0


def response_latency_p95_s(cases: list[dict]) -> float:
    values = sorted(float(case.get("latency_s", 0.0)) for case in cases)
    if not values:
        return 0.0
    index = max(round(0.95 * len(values)) - 1, 0)
    return round(values[index], 4)


def human_override_rate(cases: list[dict]) -> float:
    if not cases:
        return 0.0
    return round(sum(bool(case.get("human_overridden", False)) for case in cases) / len(cases), 4)


def brief_usefulness(cases: list[dict]) -> float:
    values = [float(case.get("usefulness_rating", 0.0)) for case in cases]
    return round(mean(values), 4) if values else 0.0


def cost_per_brief_usd(cases: list[dict]) -> float:
    values = [float(case.get("cost_usd", 0.0)) for case in cases]
    return round(mean(values), 6) if values else 0.0


def _metric_result(name: str, value: float) -> MetricResult:
    threshold, lower_is_better, blocking, _weight = THRESHOLDS[name]
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
    score = 0.0
    for metric in metric_results:
        _threshold, _lower, _blocking, weight = THRESHOLDS[metric.name]
        score += weight if metric.passed else 0.0
    return round(score, 4)


def _load_cases(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        cases = json.load(handle)
    if len(cases) < 20:
        raise ValueError("Cap-01 eval fixture must contain at least 20 query/brief pairs")
    return cases


def _terms(text: str) -> set[str]:
    return {token.strip(".,;:()[]").lower() for token in text.split() if len(token.strip(".,;:()[]")) > 3}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Cap-01 eval suite")
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run_eval(args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
