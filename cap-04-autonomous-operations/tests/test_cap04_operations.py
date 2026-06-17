from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


forecast = load("agents/forecast_agent.py", "cap04_forecast_test")
risk = load("agents/risk_agent.py", "cap04_risk_test")
optimisation = load("agents/optimisation_agent.py", "cap04_optimisation_test")
replenishment = load("agents/replenishment_agent.py", "cap04_replenishment_test")
digital_twin = load("tools/digital_twin.py", "cap04_twin_test")
exception_agent = load("agents/exception_agent.py", "cap04_exception_test")
graph_module = load("agents/supply_chain_graph.py", "cap04_graph_test")
eval_suite = load("evals/suite.py", "cap04_eval_test")


def data() -> tuple[list[dict], list[dict], list[dict]]:
    root = ROOT / "tests" / "fixtures" / "data"
    return _read(root / "sales_history.csv"), _read(root / "stock_levels.csv"), _read(root / "supplier_catalog.csv")


def test_generated_data_has_100_skus_and_90_days() -> None:
    sales, stock, suppliers = data()
    assert len({row["sku"] for row in sales}) == 100
    assert len(sales) == 9000
    assert len(stock) == 100
    assert len(suppliers) == 100


def test_forecast_backtest_mape_under_target() -> None:
    sales, _stock, _suppliers = data()
    train = [row for row in sales if int(row["day"]) <= 76]
    actual_rows = [row for row in sales if int(row["day"]) > 76]
    forecasts = forecast.forecast_demand(train, horizon_days=14)
    actual = [sum(float(row["units"]) for row in actual_rows if row["sku"] == item["sku"]) for item in forecasts]
    predicted = [item["daily_forecast"] * 14 for item in forecasts]
    assert forecast.mape(actual, predicted) <= 0.15
    assert {"lower_ci", "upper_ci", "confidence"} <= set(forecasts[0])


def test_risk_and_optimisation_outputs_expected_metrics() -> None:
    sales, stock, suppliers = data()
    forecasts = forecast.forecast_demand([row for row in sales if row["sku"] in {"SKU-001", "SKU-002"}], horizon_days=30)
    risks = risk.compute_inventory_risks(forecasts, stock[:2], suppliers[:2])
    recs = optimisation.optimise_replenishment(forecasts, risks, suppliers[:2])
    assert 0.0 <= risks[0]["stockout_probability"] <= 1.0
    assert risks[0]["days_of_cover"] >= 0
    assert "overstock_risk_score" in risks[0]
    assert recs[0]["eoq"] > 0
    assert recs[0]["safety_stock"] >= 0


def test_replenishment_uses_settings_threshold(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("AUTONOMOUS_ACTION_THRESHOLD_USD", "100")
    from core.utils.settings import get_settings

    get_settings.cache_clear()
    state = replenishment.replenishment_node({"replenishment_recommendations": [{"sku": "SKU-001", "supplier_id": "s", "recommended_qty": 20, "unit_cost": 10, "value_usd": 200}]})
    assert state["po_drafts"][0]["classification"] == "HUMAN_APPROVAL"


def test_digital_twin_runs_before_approval_context() -> None:
    result = digital_twin.simulate_po_impact({"po_id": "PO-1", "sku": "SKU-001", "quantity": 100, "unit_cost": 10, "value_usd": 1000}, {"daily_forecast": 10}, {"current_stock": 20, "stockout_probability": 0.8})
    assert result["simulated"] is True
    assert result["stockout_reduction"] > 0


def test_exception_detection_recall() -> None:
    sales, stock, suppliers = data()
    detected = exception_agent.detect_exceptions({"sales_history": sales, "stock_levels": stock, "supplier_catalog": suppliers})
    expected = _read(ROOT / "tests" / "fixtures" / "data" / "exceptions.csv")
    detected_keys = {(event["sku"], event["type"]) for event in detected}
    expected_keys = {(event["sku"], event["type"]) for event in expected}
    assert len(detected_keys & expected_keys) / len(expected_keys) >= 0.90


def test_graph_pauses_for_above_threshold_and_resumes(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("AUTONOMOUS_ACTION_THRESHOLD_USD", "100")
    from core.utils.settings import get_settings

    get_settings.cache_clear()
    sales, stock, suppliers = data()
    graph = graph_module.build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "cap04-test"}}
    state = graph_module.initial_state(run_id="cap04-test", sales_history=sales[:90], stock_levels=stock[:1], supplier_catalog=suppliers[:1])
    paused = graph.invoke(state, config=config)
    assert "__interrupt__" in paused
    payload = paused["__interrupt__"][0].value
    assert payload["simulation_results"]
    resumed = graph.invoke(Command(resume={"status": "approved", "approver_id": "planner"}), config=config)
    assert resumed["human_approval_status"] == "approved"
    assert resumed["erp_writes"]


def test_postgres_checkpointer_factory_rejects_invalid_url() -> None:
    try:
        with graph_module.build_postgres_checkpointer("sqlite://local"):
            pass
    except ValueError as exc:
        assert "Invalid PostgreSQL" in str(exc)
    else:
        raise AssertionError("invalid URL should fail")


def test_eval_suite_passes_blocking_gates() -> None:
    report = eval_suite.run_eval()
    assert report["status"] == "pass"
    assert report["metrics"]["human_approval_coverage"] == 1.0
    assert report["metrics"]["digital_twin_validation"] == 1.0


def test_state_is_json_serialisable() -> None:
    sales, stock, suppliers = data()
    state = graph_module.initial_state(run_id="json", sales_history=sales[:90], stock_levels=stock[:1], supplier_catalog=suppliers[:1])
    json.dumps(state)


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
