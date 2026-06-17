"""Discovery sub-agent using catalog connector and margin ranking."""

from __future__ import annotations

from typing import Any

from cap03_loader import load_attr

CatalogConnector = load_attr("cap03_catalog", "tools/connectors/catalog.py", "CatalogConnector")
rank_products = load_attr("cap03_margin_ranker", "tools/margin_ranker.py", "rank_products")


def discovery_node(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("search_query") or state.get("raw_message", ""))
    catalog = state.get("catalog_connector") or CatalogConnector()
    products = catalog.search(query)
    recommendations = rank_products(query, products, top_n=3)
    margin_scores = {rec.product.product_id: rec.margin_score for rec in recommendations}
    return {
        **state,
        "search_query": query,
        "catalog_results": products,
        "recommendations": recommendations,
        "margin_scores": margin_scores,
        "session_outcome": "discovery",
    }
