"""Mock promotions connector."""

from __future__ import annotations


class PromotionsConnector:
    def get_applicable_promotions(self, product_id: str) -> list[dict]:
        if product_id in {"p-espresso", "p-grinder"}:
            return [{"code": "COFFEE10", "discount_pct": 10}]
        return []

    def apply_promotion(self, basket: list[dict], code: str) -> list[dict]:
        return [{**item, "promotion": code} for item in basket]
