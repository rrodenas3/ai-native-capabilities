"""Knowledge graph update agent for compliance obligations."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cap05_loader import load_attr  # noqa: E402

KnowledgeGraph = load_attr("cap05_kg", "tools/knowledge_graph.py", "KnowledgeGraph")
GovernedKnowledgeGraph = load_attr("cap05_governed_kg", "tools/governed_kg.py", "GovernedKnowledgeGraph")


def upsert_obligations(graph: Any, regulation: dict[str, Any], articles: list[dict[str, Any]], obligations: list[dict[str, Any]]) -> Any:
    graph.add_node("Regulation", str(regulation["id"]), regulation)
    article_by_id = {}
    for article in articles:
        article_id = str(article["id"])
        article_by_id[article_id] = article
        graph.add_node("Article", article_id, article)
        graph.add_edge(str(regulation["id"]), "HAS_ARTICLE", article_id)
    for obligation in obligations:
        if not obligation.get("anchor_text") or not obligation.get("article_reference"):
            raise ValueError("obligation must include anchor_text and article_reference")
        obligation_id = str(obligation["id"])
        graph.add_node("Obligation", obligation_id, obligation)
        article_id = str(obligation["article_id"])
        if article_id not in article_by_id:
            graph.add_node("Article", article_id, {"id": article_id, "regulation_id": regulation["id"], "number": obligation["article_reference"], "title": obligation["article_reference"], "text": ""})
            graph.add_edge(str(regulation["id"]), "HAS_ARTICLE", article_id)
        graph.add_edge(article_id, "HAS_OBLIGATION", obligation_id, {"citation": obligation["anchor_text"]})
    return graph
