"""Demand forecast agent for Cap-04."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any


def forecast_node(state: dict[str, Any]) -> dict[str, Any]:
    history = list(state.get("sales_history", []))
    horizon = int(state.get("time_horizon_days", 30))
    forecasts = forecast_demand(history, horizon_days=horizon)
    anomaly_flags = list(state.get("anomaly_flags", []))
    for forecast in forecasts:
        uncertainty = forecast["uncertainty_pct"]
        if uncertainty > 0.30:
            anomaly_flags.append(
                {
                    "type": "low_confidence_forecast",
                    "sku": forecast["sku"],
                    "severity": "medium",
                    "uncertainty_pct": uncertainty,
                }
            )
    return {
        **state,
        "demand_forecasts": forecasts,
        "forecast_confidence": {item["sku"]: item["confidence"] for item in forecasts},
        "anomaly_flags": anomaly_flags,
        "human_approval_required": bool(anomaly_flags) or state.get("human_approval_required", False),
    }


def forecast_demand(history: list[dict[str, Any]], *, horizon_days: int = 30) -> list[dict[str, Any]]:
    by_sku: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in history:
        by_sku[str(row["sku"])].append(row)
    forecasts = []
    for sku, rows in sorted(by_sku.items()):
        rows = sorted(rows, key=lambda row: row["day"])
        recent = [float(row["units"]) for row in rows[-14:]]
        prior = [float(row["units"]) for row in rows[-28:-14]] or recent
        recent_avg = mean(recent) if recent else 0.0
        prior_avg = mean(prior) if prior else recent_avg
        trend = (recent_avg - prior_avg) / max(len(recent), 1)
        forecast_daily = max(0.0, recent_avg + trend * 7)
        sigma = pstdev(recent) if len(recent) > 1 else max(forecast_daily * 0.1, 0.01)
        if sigma == 0:
            sigma = max(forecast_daily * 0.1, 0.01)
        uncertainty = sigma / forecast_daily if forecast_daily > 0 else 1.0
        forecasts.append(
            {
                "sku": sku,
                "daily_forecast": round(forecast_daily, 3),
                "horizon_days": horizon_days,
                "total_forecast": round(forecast_daily * horizon_days, 3),
                "lower_ci": round(max(0.0, (forecast_daily - 1.96 * sigma) * horizon_days), 3),
                "upper_ci": round((forecast_daily + 1.96 * sigma) * horizon_days, 3),
                "confidence": round(max(0.0, min(1.0, 1.0 - uncertainty)), 3),
                "uncertainty_pct": round(uncertainty, 3),
            }
        )
    return forecasts


def mape(actual: list[float], forecast: list[float]) -> float:
    pairs = [(a, f) for a, f in zip(actual, forecast, strict=False) if a != 0]
    if not pairs:
        return 0.0
    return sum(abs(actual_value - forecast_value) / actual_value for actual_value, forecast_value in pairs) / len(pairs)
