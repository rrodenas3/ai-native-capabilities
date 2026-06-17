"""Generate deterministic synthetic Cap-04 data."""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path


def generate(seed: int = 42) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    random.seed(seed)
    sales_history = []
    stock_levels = []
    supplier_catalog = []
    exceptions = []
    for sku_index in range(1, 101):
        sku = f"SKU-{sku_index:03d}"
        base = 18 + (sku_index % 12)
        trend = (sku_index % 5) * 0.03
        for day in range(1, 91):
            seasonal = 3 * math.sin(day / 7)
            spike = 25 if sku_index <= 5 and day == 90 else 0
            units = max(1, round(base + trend * day + seasonal + random.uniform(-1.5, 1.5) + spike))
            sales_history.append({"sku": sku, "day": day, "units": units, "location": "DC-1"})
        stock = 45 if sku_index <= 20 else 180 + sku_index
        stock_levels.append({"sku": sku, "location": "DC-1", "on_hand": stock, "reorder_point": 70})
        supplier_catalog.append(
            {
                "sku": sku,
                "supplier_id": "supplier-a" if sku_index % 2 else "supplier-b",
                "lead_time_days": 7 + (sku_index % 4),
                "lead_time_change_pct": 0.25 if 6 <= sku_index <= 10 else 0.0,
                "supplier_failure": sku_index in {11, 12},
                "unit_cost": 12 + (sku_index % 8),
                "order_cost": 45,
                "holding_cost": 3,
                "moq": 10,
                "location": "DC-1",
            }
        )
        if sku_index <= 5:
            exceptions.append({"sku": sku, "type": "demand_spike"})
        if 6 <= sku_index <= 10:
            exceptions.append({"sku": sku, "type": "lead_time_change"})
        if sku_index in {11, 12}:
            exceptions.append({"sku": sku, "type": "supplier_failure"})
        if sku_index <= 20:
            exceptions.append({"sku": sku, "type": "stock_breach"})
    return sales_history, stock_levels, supplier_catalog, exceptions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sales, stock, suppliers, exceptions = generate(args.seed)
    _write_csv(args.output / "sales_history.csv", sales)
    _write_csv(args.output / "stock_levels.csv", stock)
    _write_csv(args.output / "supplier_catalog.csv", suppliers)
    _write_csv(args.output / "exceptions.csv", exceptions)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
