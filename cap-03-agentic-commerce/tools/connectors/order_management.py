"""Mock order-management connector."""

from __future__ import annotations

from threading import Lock


class OrderManagementConnector:
    def __init__(self) -> None:
        self.orders = {
            "1001": {"order_id": "1001", "status": "shipped", "items": ["p-espresso"], "returnable": True},
            "1002": {"order_id": "1002", "status": "processing", "items": ["p-tablet"], "returnable": False},
        }
        self._next_order_id = 2003
        self._lock = Lock()

    def get_order(self, order_id: str) -> dict | None:
        return self.orders.get(order_id)

    def create_order(self, customer_id: str, items: list[str], *, confirmed: bool = False) -> dict:
        if not confirmed:
            raise ValueError("Order confirmation required before OMS write")
        with self._lock:
            order_id = str(self._next_order_id)
            self._next_order_id += 1
        self.orders[order_id] = {"order_id": order_id, "customer_id": customer_id, "items": items, "status": "created"}
        return self.orders[order_id]

    def initiate_return(self, order_id: str) -> dict:
        order = self.get_order(order_id)
        if order is None:
            return {"status": "not_found"}
        if not order.get("returnable"):
            return {"status": "not_returnable", "order_id": order_id}
        return {"status": "return_started", "order_id": order_id}
