"""Inventory risk agent for Cap-04."""

from __future__ import annotations

from typing import Any


def risk_node(state: dict[str, Any]) -> dict[str, Any]:
    risks = compute_inventory_risks(
        list(state.get("demand_forecasts", [])),
        list(state.get("stock_levels", [])),
        list(state.get("supplier_catalog", [])),
    )
    return {**state, "inventory_risks": risks}


def compute_inventory_risks(
    forecasts: list[dict[str, Any]],
    stock_levels: list[dict[str, Any]],
    supplier_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    stock_by_sku = {row["sku"]: float(row["on_hand"]) for row in stock_levels}
    supplier_by_sku = {row["sku"]: row for row in supplier_catalog}
    risks = []
    for forecast in forecasts:
        sku = forecast["sku"]
        supplier = supplier_by_sku.get(sku, {})
        lead_time = int(supplier.get("lead_time_days", 7))
        daily = float(forecast["daily_forecast"])
        stock = stock_by_sku.get(sku, 0.0)
        lead_time_demand = daily * lead_time
        days_cover = stock / daily if daily > 0 else 999.0
        stockout_probability = min(1.0, max(0.0, (lead_time_demand - stock) / max(lead_time_demand, 1.0)))
        overstock_risk = min(1.0, max(0.0, (days_cover - 60) / 60))
        risks.append(
            {
                "sku": sku,
                "location": supplier.get("location", "default"),
                "stockout_probability": round(stockout_probability, 3),
                "days_of_cover": round(days_cover, 2),
                "overstock_risk_score": round(overstock_risk, 3),
                "current_stock": stock,
                "lead_time_days": lead_time,
            }
        )
    return risks
