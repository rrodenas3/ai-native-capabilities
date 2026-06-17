"""ERP/WMS write node for approved Cap-04 actions."""

from __future__ import annotations

from typing import Any

from cap04_loader import load_attr

ERPConnector = load_attr("cap04_erp", "tools/connectors/erp.py", "ERPConnector")
WMSConnector = load_attr("cap04_wms", "tools/connectors/wms.py", "WMSConnector")


def erp_wms_node(state: dict[str, Any]) -> dict[str, Any]:
    erp = ERPConnector()
    wms = WMSConnector()
    approved = state.get("human_approval_status") in {"approved", "modified", "not_required"}
    erp_writes = []
    wms_updates = []
    for po in state.get("po_drafts", []):
        if po.get("classification") == "HUMAN_APPROVAL" and not approved:
            continue
        created = erp.create_po(po, approved=approved)
        erp_writes.append(created)
        wms_updates.append(wms.update_expected_receipt(created))
    return {**state, "erp_writes": erp_writes, "wms_updates": wms_updates}
