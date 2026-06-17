"""Demo for querying the Cap-05 compliance obligation register."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cap05_loader import load_attr  # noqa: E402

extract_from_articles = load_attr("cap05_demo_interpret", "agents/interpretation_agent.py", "extract_from_articles")
ExpertReviewGate = load_attr("cap05_demo_gate", "agents/expert_gate.py", "ExpertReviewGate")
answer_query = load_attr("cap05_demo_query", "agents/query_agent.py", "answer_query")
load_articles = load_attr("cap05_demo_eval", "evals/suite.py", "load_articles")

_DEFAULT_QUERY = "What are the Annex III high-risk AI system obligations?"


def run_demo(query: str = _DEFAULT_QUERY) -> dict:
    articles = load_articles(limit=15)
    extracted = extract_from_articles(articles)
    gate = ExpertReviewGate()
    confirmed = []
    for obligation in extracted:
        gate.queue_for_review(obligation)
        confirmed.append(gate.submit_review(obligation["id"], "CONFIRM", "demo-legal-reviewer"))
    answers = answer_query(query, confirmed)
    return {"query": query, "answers": answers[:5], "audit_events": len(gate.audit_trail.events)}


def _build_report(result: dict) -> dict:
    """Wrap demo result in the canonical report envelope."""
    answers = result.get("answers", [])
    citation_rate = sum(1 for a in answers if a.get("citations")) / len(answers) if answers else 0.0
    return {
        "cap": "cap-05",
        "status": "pass",
        "score": citation_rate,
        "metrics": {
            "query_answer_citation_rate": citation_rate,
            "audit_events": result.get("audit_events", 0),
        },
        "blocking_failures": [],
        "query": result.get("query", ""),
        "answers": answers,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cap-05 compliance obligation demo")
    parser.add_argument(
        "--query",
        default=_DEFAULT_QUERY,
        help="Compliance question to answer (default: Annex III high-risk AI obligations)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write JSON report to FILE in the standard report envelope format",
    )
    args = parser.parse_args()

    result = run_demo(query=args.query)

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            report = _build_report(result)
            output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: could not write output to {args.output}: {exc}", file=sys.stderr)
            sys.exit(1)

    print(json.dumps(result, indent=2))
