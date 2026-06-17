"""Replenishment optimisation agent for Cap-04."""

from __future__ import annotations

import math
from typing import Any


def optimisation_node(state: dict[str, Any]) -> dict[str, Any]:
    recommendations = optimise_replenishment(
        list(state.get("demand_forecasts", [])),
        list(state.get("inventory_risks", [])),
        list(state.get("supplier_catalog", [])),
    )
    return {**state, "replenishment_recommendations": recommendations}


def optimise_replenishment(
    forecasts: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    supplier_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    forecast_by_sku = {row["sku"]: row for row in forecasts}
    supplier_by_sku = {row["sku"]: row for row in supplier_catalog}
    recommendations = []
    for risk in risks:
        sku = risk["sku"]
        forecast = forecast_by_sku[sku]
        supplier = supplier_by_sku.get(sku, {})
        annual_demand = float(forecast["daily_forecast"]) * 365
        order_cost = float(supplier.get("order_cost", 45.0))
        unit_cost = float(supplier.get("unit_cost", 10.0))
        holding_cost = float(supplier.get("holding_cost", unit_cost * 0.2))
        eoq = math.sqrt((2 * annual_demand * order_cost) / max(holding_cost, 0.01))
        safety_stock = 1.65 * (float(forecast["uncertainty_pct"]) * float(forecast["daily_forecast"])) * math.sqrt(float(risk["lead_time_days"]))
        reorder_qty = max(0.0, eoq + safety_stock - float(risk["current_stock"]))
        moq = float(supplier.get("moq", 1))
        reorder_qty = max(moq if risk["stockout_probability"] > 0.2 else 0.0, reorder_qty)
        recommendations.append(
            {
                "sku": sku,
                "supplier_id": supplier.get("supplier_id", "supplier-default"),
                "recommended_qty": int(round(reorder_qty)),
                "eoq": round(eoq, 3),
                "safety_stock": round(safety_stock, 3),
                "unit_cost": unit_cost,
                "value_usd": round(int(round(reorder_qty)) * unit_cost, 2),
                "stockout_probability": risk["stockout_probability"],
            }
        )
    return recommendations
