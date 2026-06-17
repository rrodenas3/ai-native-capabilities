"""ERP/WMS write node for approved Cap-04 actions."""

from __future__ import annotations

from typing import Any

from cap04_loader import load_attr

ERPConnector = load_attr("cap04_erp", "tools/connectors/erp.py", "ERPConnector")
WMSConnector = load_attr("cap04_wms", "tools/connectors/wms.py", "WMSConnector")
GovernedPOStore = load_attr("cap04_governed_po_store", "tools/governed_po_store.py", "GovernedPOStore")


def erp_wms_node(state: dict[str, Any]) -> dict[str, Any]:
    erp = ERPConnector()
    wms = WMSConnector()
    approved = state.get("human_approval_status") in {"approved", "modified", "not_required"}

    store = GovernedPOStore(capability="cap-04", quarantine_threshold=0.5)
    for po in state.get("po_drafts", []):
        store.add_draft(po)

    audit_trail = list(state.get("audit_trail") or [])
    for record in store.quarantined:
        audit_trail.append({
            "event": "po_quarantined",
            "po_id": record["po_id"],
            "sku": record["sku"],
            "reason": record["reason"],
        })

    erp_writes = []
    wms_updates = []
    for po in store.approved_drafts:
        if po.get("classification") == "HUMAN_APPROVAL" and not approved:
            continue
        try:
            created = erp.create_po(po, approved=approved)
            erp_writes.append(created)
            wms_updates.append(wms.update_expected_receipt(created))
        except PermissionError:
            continue

    return {
        **state,
        "erp_writes": erp_writes,
        "wms_updates": wms_updates,
        "audit_trail": audit_trail,
        "quarantine_count": store.quarantine_count,
    }
