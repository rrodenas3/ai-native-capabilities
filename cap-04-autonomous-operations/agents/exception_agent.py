"""Exception handler for Cap-04 operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, pstdev
from typing import Any


class ExceptionDeduper:
    def __init__(self) -> None:
        self.last_seen: dict[tuple[str, str], datetime] = {}

    def should_emit(self, event: dict[str, Any], now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        key = (str(event.get("type")), str(event.get("sku", "*")))
        previous = self.last_seen.get(key)
        self.last_seen[key] = now
        return previous is None or now - previous > timedelta(hours=1)


def exception_node(state: dict[str, Any]) -> dict[str, Any]:
    events = detect_exceptions(state)
    return {**state, "exception_events": events, "human_approval_required": bool(events) or state.get("human_approval_required", False)}


def detect_exceptions(state: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    history_by_sku: dict[str, list[float]] = {}
    for row in state.get("sales_history", []):
        history_by_sku.setdefault(str(row["sku"]), []).append(float(row["units"]))
    for sku, values in history_by_sku.items():
        if len(values) >= 10:
            baseline = values[:-1]
            sigma = pstdev(baseline) or 1.0
            z_score = (values[-1] - mean(baseline)) / sigma
            if z_score > 2:
                events.append({"type": "demand_spike", "sku": sku, "severity": "high", "z_score": round(z_score, 3)})
    for supplier in state.get("supplier_catalog", []):
        if float(supplier.get("lead_time_change_pct", 0.0)) > 0.20:
            events.append({"type": "lead_time_change", "sku": supplier["sku"], "severity": "medium"})
        if supplier.get("supplier_failure"):
            events.append({"type": "supplier_failure", "sku": supplier["sku"], "severity": "critical"})
    for stock in state.get("stock_levels", []):
        if float(stock.get("on_hand", 0.0)) <= float(stock.get("reorder_point", 0.0)):
            events.append({"type": "stock_breach", "sku": stock["sku"], "severity": "high"})
    return events
