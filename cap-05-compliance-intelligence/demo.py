"""Demo for querying the Cap-05 compliance obligation register."""

from __future__ import annotations

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


def run_demo(query: str = "What are Article 13 obligations?") -> dict:
    articles = load_articles(limit=15)
    extracted = extract_from_articles(articles)
    gate = ExpertReviewGate()
    confirmed = []
    for obligation in extracted:
        gate.queue_for_review(obligation)
        confirmed.append(gate.submit_review(obligation["id"], "CONFIRM", "demo-legal-reviewer"))
    answers = answer_query(query, confirmed)
    return {"query": query, "answers": answers[:5], "audit_events": len(gate.audit_trail.events)}


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
