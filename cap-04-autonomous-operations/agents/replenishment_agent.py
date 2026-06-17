"""PO draft and replenishment action agent."""

from __future__ import annotations

from typing import Any

from core.utils.settings import get_settings


def replenishment_node(state: dict[str, Any]) -> dict[str, Any]:
    threshold = float(get_settings().AUTONOMOUS_ACTION_THRESHOLD_USD)
    po_drafts = []
    approval_required = bool(state.get("human_approval_required", False))
    for index, rec in enumerate(state.get("replenishment_recommendations", []), start=1):
        if int(rec["recommended_qty"]) <= 0:
            continue
        value = float(rec["value_usd"])
        classification = "HUMAN_APPROVAL" if value >= threshold or approval_required else "AUTONOMOUS"
        if classification == "HUMAN_APPROVAL":
            approval_required = True
        po_drafts.append(
            {
                "po_id": f"PO-DRAFT-{index:03d}",
                "sku": rec["sku"],
                "supplier_id": rec["supplier_id"],
                "quantity": int(rec["recommended_qty"]),
                "unit_cost": rec["unit_cost"],
                "value_usd": value,
                "classification": classification,
                "threshold_usd": threshold,
                "status": "draft",
            }
        )
    return {**state, "po_drafts": po_drafts, "human_approval_required": approval_required}
