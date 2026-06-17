"""Mock WMS connector for Cap-04."""

from __future__ import annotations

from typing import Any


class WMSConnector:
    def __init__(self, stock_levels: list[dict[str, Any]] | None = None) -> None:
        self.stock_levels = stock_levels or []
        self.expected_receipts: list[dict[str, Any]] = []

    def get_stock_levels(self) -> list[dict[str, Any]]:
        return list(self.stock_levels)

    def update_expected_receipt(self, po: dict[str, Any]) -> dict[str, Any]:
        receipt = {"sku": po["sku"], "quantity": po["quantity"], "po_id": po.get("erp_po_id", po["po_id"]), "status": "expected"}
        self.expected_receipts.append(receipt)
        return receipt
