"""Mock ERP connector for Cap-04."""

from __future__ import annotations

from typing import Any


class ERPConnector:
    def __init__(self, budget_usd: float = 100_000.0) -> None:
        self.budget_usd = budget_usd
        self.purchase_orders: list[dict[str, Any]] = []

    def get_budget(self) -> dict[str, float]:
        spent = sum(float(po["value_usd"]) for po in self.purchase_orders)
        return {"budget_usd": self.budget_usd, "spent_usd": round(spent, 2), "remaining_usd": round(self.budget_usd - spent, 2)}

    def get_suppliers(self) -> list[dict[str, Any]]:
        return [{"supplier_id": "supplier-a", "name": "Acme Supply", "currency": "USD"}]

    def create_po(self, po_draft: dict[str, Any], *, approved: bool) -> dict[str, Any]:
        if po_draft.get("classification") == "HUMAN_APPROVAL" and not approved:
            raise PermissionError("Human approval required for high-value PO")
        po = {**po_draft, "status": "created", "erp_po_id": f"ERP-{len(self.purchase_orders) + 1:05d}"}
        self.purchase_orders.append(po)
        return po
