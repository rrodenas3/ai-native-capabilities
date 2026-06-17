"""Mock product catalog connector."""

from __future__ import annotations

from cap03_schema_loader import Product

PRODUCTS = [
    Product(product_id="p-espresso", name="Barista Pro Espresso Machine", category="kitchen", price=799, cost=520, stock=6, tags=["espresso", "coffee", "gift"]),
    Product(product_id="p-grinder", name="Precision Burr Grinder", category="kitchen", price=199, cost=90, stock=14, tags=["coffee", "grinder"]),
    Product(product_id="p-beans", name="Organic Espresso Beans", category="grocery", price=18, cost=9, stock=90, tags=["coffee", "beans"]),
    Product(product_id="p-tablet", name="Kids Learning Tablet", category="electronics", price=149, cost=130, stock=8, tags=["tablet", "kids", "learning"]),
    Product(product_id="p-oos", name="Limited Smart Speaker", category="electronics", price=99, cost=40, stock=0, tags=["speaker", "smart"]),
    Product(product_id="p-negative", name="Clearance Camera Bundle", category="electronics", price=120, cost=150, stock=5, tags=["camera", "bundle"]),
]


class CatalogConnector:
    def search(self, query: str, filters: dict | None = None) -> list[Product]:
        terms = {term for term in query.lower().split() if len(term) > 2}
        results = []
        for product in PRODUCTS:
            haystack = " ".join([product.name, product.category, *product.tags]).lower()
            if not terms or any(term in haystack for term in terms):
                results.append(product)
        return results

    def get_product(self, product_id: str) -> Product | None:
        return next((product for product in PRODUCTS if product.product_id == product_id), None)

    def check_availability(self, product_id: str) -> bool:
        product = self.get_product(product_id)
        return bool(product and product.stock > 0)

    def get_pricing(self, product_id: str) -> dict[str, float]:
        product = self.get_product(product_id)
        if product is None:
            return {}
        return {"price": product.price, "cost": product.cost}
