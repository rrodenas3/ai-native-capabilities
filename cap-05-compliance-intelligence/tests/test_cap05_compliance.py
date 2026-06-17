from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

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


feed = load("tools/feed_monitor.py", "cap05_feed_test")
classifier = load("agents/classifier_agent.py", "cap05_classifier_test")
interpretation = load("agents/interpretation_agent.py", "cap05_interpret_test")
kg_module = load("tools/knowledge_graph.py", "cap05_kg_test")
kg_agent = load("agents/kg_agent.py", "cap05_kg_agent_test")
expert = load("agents/expert_gate.py", "cap05_expert_test")
inventory_module = load("tools/connectors/use_case_inventory.py", "cap05_inventory_test")
gap_agent = load("agents/gap_agent.py", "cap05_gap_test")
query_agent = load("agents/query_agent.py", "cap05_query_test")
audit_module = load("tools/audit_trail.py", "cap05_audit_test")
eval_suite = load("evals/suite.py", "cap05_eval_test")


def test_feed_monitor_dedupes_and_queues_within_60_minutes() -> None:
    monitor = feed.RegulatoryFeedMonitor()
    docs = [
        {"source": "EUR-Lex", "title": "EU AI Act", "url": "https://example.test/doc?utm=1", "published_at": "2026-01-01T00:00:00+00:00", "text": "Providers shall comply."},
        {"source": "EUR-Lex", "title": "EU AI Act", "url": "https://example.test/doc", "published_at": "2026-01-01T12:00:00+00:00", "text": "Duplicate copy."},
        {"source": "NIST CSRC", "title": "NIST AI guidance", "url": "https://nist.example/ai", "published_at": "2026-01-02", "text": "Guidance for AI risk."},
    ]
    queued = monitor.poll_feeds(docs)
    assert len(queued) == 2
    assert monitor.queue_latency_hours(queued[0]) <= 1.0


def test_classifier_handles_20_document_set() -> None:
    docs = []
    labels = ["REGULATION", "AMENDMENT", "GUIDANCE", "ENFORCEMENT"] * 5
    text_by_label = {
        "REGULATION": "European Union AI Act regulation for employment effective 2026-08-02.",
        "AMENDMENT": "Omnibus amendment amending the EU AI Act.",
        "GUIDANCE": "NIST AI guidance and code of practice.",
        "ENFORCEMENT": "Enforcement action with penalty and fine.",
    }
    for index, label in enumerate(labels):
        docs.append({"id": f"doc-{index}", "source": "EUR-Lex", "title": label, "text": text_by_label[label]})
    classified = [classifier.classify_document(doc) for doc in docs]
    assert [item.document_type for item in classified] == labels
    assert all(item.effective_dates for item in classified)
    assert all(item.jurisdiction in {"EU", "US"} for item in classified)


def test_obligation_extraction_hits_known_eu_ai_act_anchors() -> None:
    articles = eval_suite.load_articles()
    known = json.loads((ROOT / "tests" / "fixtures" / "corpus" / "eu_ai_act" / "known_obligations.json").read_text(encoding="utf-8"))
    extracted = interpretation.extract_from_articles(articles)
    extracted_anchors = {item["anchor_text"] for item in extracted}
    assert {item["anchor_text"] for item in known} <= extracted_anchors
    assert all(item["anchor_text"] in next(article["text"] for article in articles if article["id"] == item["article_id"]) for item in extracted)
    assert {item["extraction_model"] for item in extracted} == {"claude-opus-4-8"}


def test_kg_expert_gate_gap_and_query_flow() -> None:
    articles = eval_suite.load_articles(limit=10)
    obligations = interpretation.extract_from_articles(articles)
    gate = expert.ExpertReviewGate()
    confirmed = []
    for obligation in obligations[:10]:
        gate.queue_for_review(obligation)
        confirmed.append(gate.submit_review(obligation["id"], "CONFIRM", "legal-reviewer"))
    graph = kg_module.KnowledgeGraph()
    kg_agent.upsert_obligations(graph, {"id": "reg-eu-ai-act", "name": "EU AI Act", "jurisdiction": "EU"}, articles, confirmed)
    inventory = inventory_module.UseCaseInventory()
    for use_case in inventory.list_use_cases():
        graph.add_node("UseCase", use_case["id"], use_case)
    gaps = gap_agent.detect_gaps(confirmed, inventory.list_use_cases())
    assert gaps
    gap_agent.write_gaps_to_graph(graph, gaps)
    answers = query_agent.answer_query("Article 2 high-risk obligations", confirmed)
    assert answers
    assert query_agent.citation_rate(answers) == 1.0
    assert all(answer["status"] == "CONFIRMED" for answer in answers)
    assert graph.relationship_counts()["HAS_OBLIGATION"] >= 10


def test_expert_gate_blocks_unreviewed_obligation_and_audit_is_immutable() -> None:
    obligation = interpretation.extract_obligations({"article_reference": "Article 1", "text": "Providers shall maintain records."})[0]
    try:
        expert.require_confirmed(obligation)
    except PermissionError:
        pass
    else:
        raise AssertionError("unreviewed obligation should be blocked")
    audit = audit_module.AuditTrail()
    audit.log_event("test", {"id": "event"})
    try:
        audit.update_event("audit-000001", {})
    except PermissionError:
        pass
    else:
        raise AssertionError("audit trail update should be rejected")
    assert audit.verify_integrity()


def test_eval_suite_passes_all_blocking_gates() -> None:
    report = eval_suite.run_eval()
    assert report["status"] == "pass"
    assert report["metrics"]["false_negative_rate_obligations"] <= 0.01
    assert report["metrics"]["expert_review_coverage"] == 1.0
    assert report["metrics"]["query_answer_citation_rate"] == 1.0
