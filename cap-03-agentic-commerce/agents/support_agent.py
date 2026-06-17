"""Support sub-agent with policy citations and live OMS lookups."""

from __future__ import annotations

import re
from typing import Any

from cap03_loader import load_attr
from cap03_schema_loader import ResolutionResult, ResolutionType

OrderManagementConnector = load_attr("cap03_oms", "tools/connectors/order_management.py", "OrderManagementConnector")


POLICIES = {
    "returns": "Policy RETURNS-01: Most shipped items may be returned within 30 days with proof of purchase.",
    "shipping": "Policy SHIPPING-02: Standard shipments receive tracking updates when the carrier scans the package.",
    "warranty": "Policy WARRANTY-03: Electronics warranty claims require the order id and product serial number.",
}


def support_node(state: dict[str, Any]) -> dict[str, Any]:
    message = str(state.get("raw_message", ""))
    oms = state.get("oms_connector") or OrderManagementConnector()
    order_id = _order_id(message)
    citations: list[str] = []
    if order_id:
        order = oms.get_order(order_id)
        if order is None:
            result = ResolutionResult(
                resolution_type=ResolutionType.INFORMATION,
                resolution_text=f"I could not find live order data for order {order_id}.",
                order_id=order_id,
            )
        elif "return" in message.lower() or "refund" in message.lower():
            action = oms.initiate_return(order_id)
            citations.append(POLICIES["returns"].split(":")[0])
            result = ResolutionResult(
                resolution_type=ResolutionType.ACTION_TAKEN if action["status"] == "return_started" else ResolutionType.INFORMATION,
                resolution_text=f"Live OMS status for order {order_id}: {order.get('status', 'unknown')}. Return result: {action.get('status', 'unknown')}.",
                citations=citations,
                order_id=order_id,
            )
        else:
            citations.append(POLICIES["shipping"].split(":")[0])
            result = ResolutionResult(
                resolution_type=ResolutionType.INFORMATION,
                resolution_text=f"Live OMS status for order {order_id}: {order.get('status', 'unknown')}.",
                citations=citations,
                order_id=order_id,
            )
    else:
        key = "returns" if re.search(r"return|refund", message, re.I) else "shipping"
        citations.append(POLICIES[key].split(":")[0])
        result = ResolutionResult(
            resolution_type=ResolutionType.INFORMATION,
            resolution_text=POLICIES[key],
            citations=citations,
        )
    return {**state, "resolution": result, "session_outcome": "deflected"}


def _order_id(message: str) -> str | None:
    match = re.search(r"\b(?:order\s*)?(\d{4})\b", message)
    return match.group(1) if match else None
