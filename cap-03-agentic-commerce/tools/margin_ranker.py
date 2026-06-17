"""Margin-aware product ranking."""

from __future__ import annotations

from cap03_schema_loader import Product, Recommendation


def margin_score(product: Product) -> float:
    if product.price <= 0:
        return -1.0
    return round((product.price - product.cost) / product.price, 4)


def rank_products(query: str, products: list[Product], *, top_n: int = 3) -> list[Recommendation]:
    terms = {term for term in query.lower().split() if len(term) > 2}
    recommendations = []
    for product in products:
        haystack = " ".join([product.name, product.category, *product.tags]).lower()
        relevance = min(1.0, sum(term in haystack for term in terms) / max(len(terms), 1))
        stock = 1.0 if product.stock > 0 else 0.0
        margin = margin_score(product)
        combined = round((relevance * 0.6) + (max(margin, 0.0) * 0.3) + (stock * 0.1), 4)
        recommendations.append(
            Recommendation(
                product=product,
                relevance_score=relevance,
                margin_score=margin,
                stock_score=stock,
                combined_score=combined,
                rank=0,
            )
        )
    ranked = sorted(recommendations, key=lambda rec: rec.combined_score, reverse=True)
    primary_safe = [rec for rec in ranked if rec.margin_score >= 0.0 and rec.stock_score > 0]
    remainder = [rec for rec in ranked if rec not in primary_safe and rec.stock_score > 0]
    final = [*primary_safe, *remainder][:top_n]
    return [rec.model_copy(update={"rank": index}) for index, rec in enumerate(final, start=1)]
