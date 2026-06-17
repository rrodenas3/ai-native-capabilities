#!/usr/bin/env python3
"""
Generate eval summary report from all capability eval JSON files.
Called by GitHub Actions after all capability evals complete.
Writes reports/summary.md which is posted as a PR comment.

Usage:
    python scripts/eval_summary.py reports/
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CAP_NAMES = {
    "cap-01": "Decision Intelligence",
    "cap-02": "Agentic Engineering (SASE)",
    "cap-03": "Agentic Commerce",
    "cap-04": "Autonomous Operations",
    "cap-05": "Compliance Intelligence",
}

STATUS_EMOJI = {
    "pass": "✅",
    "warn": "⚠️",
    "fail": "❌",
    "missing": "⏳",
    "error": "🔴",
}

BLOCKING_METRICS = {
    "cap-01": ["citation_accuracy", "hallucination_rate"],
    "cap-02": ["briefing_completeness", "security_weakness_rate"],
    "cap-03": ["agent_sprawl_count", "escalation_accuracy"],
    "cap-04": ["human_approval_coverage", "digital_twin_validation"],
    "cap-05": [
        "false_negative_rate_obligations",
        "citation_accuracy",
        "expert_review_coverage",
        "query_answer_citation_rate",
    ],
}


def load_report(reports_dir: Path, cap_id: str) -> dict:
    """Load a capability eval report, handling missing files gracefully."""
    # GitHub Actions downloads artifacts into subdirs
    candidates = [
        reports_dir / f"{cap_id}.json",
        reports_dir / f"{cap_id}-eval-report" / f"{cap_id}.json",
        reports_dir / f"{cap_id[4:]}-eval-report" / f"{cap_id}.json",
    ]
    for path in candidates:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    return {"cap": cap_id, "status": "missing", "score": 0.0, "metrics": {}, "blocking_failures": []}


def cap_status(report: dict, cap_id: str) -> str:
    status = report.get("status", "unknown")
    if status in ("missing", "not_found", "no_eval_suite"):
        return "missing"
    if status == "error":
        return "error"
    blocking = report.get("blocking_failures", [])
    if blocking:
        return "fail"
    score = report.get("score", 0.0)
    if score >= 0.85:
        return "pass"
    return "warn"


def format_metric(value: float | None, metric_name: str, cap_id: str) -> str:
    if value is None:
        return "—"
    blocking = BLOCKING_METRICS.get(cap_id, [])
    if metric_name in blocking:
        return f"**{value:.4f}**"
    return f"{value:.4f}"


def generate_summary(reports_dir: Path) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    caps = ["cap-01", "cap-02", "cap-03", "cap-04", "cap-05"]
    reports = {cap: load_report(reports_dir, cap) for cap in caps}
    statuses = {cap: cap_status(reports[cap], cap) for cap in caps}

    all_pass = all(s == "pass" for s in statuses.values())
    any_fail = any(s in ("fail", "error") for s in statuses.values())

    # Header
    if all_pass:
        header = "## ✅ Eval Suite — All Gates Passed"
    elif any_fail:
        header = "## ❌ Eval Suite — Blocking Failures Detected"
    else:
        header = "## ⚠️ Eval Suite — Warnings Present"

    lines = [
        header,
        f"*{now} · ai-native-capabilities*",
        "",
        "### Summary",
        "",
        "| Capability | Status | Score | Blocking failures | Cost | Time |",
        "|---|---|---|---|---|---|",
    ]

    for cap in caps:
        report = reports[cap]
        name = CAP_NAMES[cap]
        st = statuses[cap]
        emoji = STATUS_EMOJI.get(st, "❓")
        score = report.get("score", 0.0)
        score_str = f"{score:.2f}" if score else "—"
        blocking = report.get("blocking_failures", [])
        blocking_str = ", ".join(blocking) if blocking else "none"
        cost = report.get("total_cost_usd", None)
        cost_str = f"${cost:.3f}" if cost else "—"
        elapsed = report.get("elapsed_s", None)
        time_str = f"{elapsed}s" if elapsed else "—"

        if st == "missing":
            lines.append(f"| **{cap}** {name} | {emoji} not built | — | eval suite pending | — | — |")
        elif st == "error":
            err = report.get("stderr", "")[:60]
            lines.append(f"| **{cap}** {name} | {emoji} error | — | {err} | — | — |")
        else:
            lines.append(f"| **{cap}** {name} | {emoji} {st} | {score_str} | {blocking_str} | {cost_str} | {time_str} |")

    lines += [""]

    # Detail sections for failures
    for cap in caps:
        report = reports[cap]
        blocking = report.get("blocking_failures", [])
        if not blocking:
            continue

        name = CAP_NAMES[cap]
        lines += [
            f"### ❌ {cap} — {name}: blocking failures",
            "",
        ]
        metrics = report.get("metrics", {})
        for metric in blocking:
            val = metrics.get(metric, "MISSING")
            lines.append(f"- `{metric}`: got `{val}` (see `{cap}/specs/SPEC.md` for threshold)")
        lines.append("")

    # Cost summary
    total_cost = sum(
        r.get("total_cost_usd", 0.0)
        for r in reports.values()
        if isinstance(r.get("total_cost_usd"), float)
    )
    if total_cost > 0:
        lines += [
            "### Cost",
            f"Total eval run cost: **${total_cost:.4f}**",
            "> Reminder: agentic multiplier is 5–30× vs single-turn. Monitor monthly budget.",
            "",
        ]

    # Footer
    lines += [
        "---",
        "*Generated by `scripts/eval_summary.py` · [Stack reference](docs/architecture/STACK.md) · [Contributing](CONTRIBUTING.md)*",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate eval summary report")
    parser.add_argument("reports_dir", help="Directory containing eval JSON reports")
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    if not reports_dir.exists():
        print(f"ERROR: reports directory not found: {reports_dir}")
        sys.exit(1)

    summary = generate_summary(reports_dir)

    output_path = reports_dir / "summary.md"
    with open(output_path, "w") as f:
        f.write(summary)

    print(summary)
    print(f"\n✓ Summary written to {output_path}")


if __name__ == "__main__":
    main()
