"""Digital twin simulation for Cap-04 PO impact."""

from __future__ import annotations

from typing import Any


def simulate_po_impact(po_draft: dict[str, Any], forecast: dict[str, Any], risk: dict[str, Any], *, horizon_days: int = 30) -> dict[str, Any]:
    daily = float(forecast.get("daily_forecast", 0.0))
    current_stock = float(risk.get("current_stock", 0.0))
    quantity = float(po_draft.get("quantity", 0.0))
    demand = daily * horizon_days
    baseline_shortage = max(0.0, demand - current_stock)
    simulated_shortage = max(0.0, demand - (current_stock + quantity))
    reduction = (baseline_shortage - simulated_shortage) / baseline_shortage if baseline_shortage else 1.0
    inventory_cost = max(0.0, current_stock + quantity - demand) * float(po_draft.get("unit_cost", 0.0)) * 0.02
    return {
        "po_id": po_draft["po_id"],
        "sku": po_draft["sku"],
        "stockout_reduction": round(max(0.0, reduction), 3),
        "inventory_cost_usd": round(inventory_cost, 2),
        "cash_impact_usd": float(po_draft.get("value_usd", 0.0)),
        "risk_score": round(float(risk.get("stockout_probability", 0.0)) * (1 - max(0.0, reduction)), 3),
        "simulated": True,
    }


def digital_twin_node(state: dict[str, Any]) -> dict[str, Any]:
    forecasts = {row["sku"]: row for row in state.get("demand_forecasts", [])}
    risks = {row["sku"]: row for row in state.get("inventory_risks", [])}
    results = [
        simulate_po_impact(po, forecasts.get(po["sku"], {}), risks.get(po["sku"], {}), horizon_days=int(state.get("time_horizon_days", 30)))
        for po in state.get("po_drafts", [])
    ]
    return {**state, "simulation_results": results}
