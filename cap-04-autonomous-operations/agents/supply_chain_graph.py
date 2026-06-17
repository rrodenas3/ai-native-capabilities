"""Stateful LangGraph for Cap-04 supply chain replenishment."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cap04_loader import load_attr  # noqa: E402

from core.utils.settings import get_settings  # noqa: E402

forecast_node = load_attr("cap04_forecast", "agents/forecast_agent.py", "forecast_node")
risk_node = load_attr("cap04_risk", "agents/risk_agent.py", "risk_node")
optimisation_node = load_attr("cap04_optimisation", "agents/optimisation_agent.py", "optimisation_node")
replenishment_node = load_attr("cap04_replenishment", "agents/replenishment_agent.py", "replenishment_node")
digital_twin_node = load_attr("cap04_digital_twin", "tools/digital_twin.py", "digital_twin_node")
approval_gate_node = load_attr("cap04_approval", "agents/approval_gate.py", "approval_gate_node")
erp_wms_node = load_attr("cap04_erp_wms", "agents/erp_wms_agent.py", "erp_wms_node")
exception_node = load_attr("cap04_exception", "agents/exception_agent.py", "exception_node")


class SupplyChainState(TypedDict, total=False):
    run_id: str
    trigger_type: str
    trigger_event: dict[str, Any] | None
    scope_skus: list[str]
    scope_locations: list[str]
    time_horizon_days: int
    sales_history: list[dict[str, Any]]
    stock_levels: list[dict[str, Any]]
    supplier_catalog: list[dict[str, Any]]
    demand_forecasts: list[dict[str, Any]]
    forecast_confidence: dict[str, float]
    anomaly_flags: list[dict[str, Any]]
    inventory_risks: list[dict[str, Any]]
    exception_events: list[dict[str, Any]]
    replenishment_recommendations: list[dict[str, Any]]
    po_drafts: list[dict[str, Any]]
    simulation_results: list[dict[str, Any]]
    autonomous_actions: list[dict[str, Any]]
    human_approval_required: bool
    human_approval_status: str | None
    human_modifications: list[dict[str, Any]] | None
    approver_id: str | None
    erp_writes: list[dict[str, Any]]
    wms_updates: list[dict[str, Any]]
    audit_trail: list[dict[str, Any]]
    quarantine_count: int
    cost_tokens: int


def build_graph(*, checkpointer: Any = None) -> CompiledStateGraph:
    graph = StateGraph(SupplyChainState)
    graph.add_node("forecast", forecast_node)
    graph.add_node("exceptions", exception_node)
    graph.add_node("risk", risk_node)
    graph.add_node("optimise", optimisation_node)
    graph.add_node("replenish", replenishment_node)
    graph.add_node("digital_twin", digital_twin_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("erp_wms", erp_wms_node)

    graph.add_edge(START, "forecast")
    graph.add_edge("forecast", "exceptions")
    graph.add_edge("exceptions", "risk")
    graph.add_edge("risk", "optimise")
    graph.add_edge("optimise", "replenish")
    graph.add_edge("replenish", "digital_twin")
    graph.add_edge("digital_twin", "approval_gate")
    graph.add_edge("approval_gate", "erp_wms")
    graph.add_edge("erp_wms", END)
    return graph.compile(checkpointer=checkpointer, name="cap-04-supply-chain")


def initial_state(*, run_id: str, sales_history: list[dict[str, Any]], stock_levels: list[dict[str, Any]], supplier_catalog: list[dict[str, Any]]) -> SupplyChainState:
    if not sales_history:
        raise ValueError("sales_history cannot be empty")
    if not stock_levels:
        raise ValueError("stock_levels cannot be empty")
    if not supplier_catalog:
        raise ValueError("supplier_catalog cannot be empty")
    return {
        "run_id": run_id,
        "trigger_type": "manual",
        "trigger_event": None,
        "scope_skus": sorted({row["sku"] for row in sales_history}),
        "scope_locations": sorted({row.get("location", "default") for row in stock_levels}),
        "time_horizon_days": 30,
        "sales_history": sales_history,
        "stock_levels": stock_levels,
        "supplier_catalog": supplier_catalog,
        "anomaly_flags": [],
        "exception_events": [],
        "simulation_results": [],
        "autonomous_actions": [],
        "human_approval_required": False,
        "human_approval_status": None,
        "human_modifications": None,
        "audit_trail": [],
        "cost_tokens": 0,
    }


@contextmanager
def build_postgres_checkpointer(database_url: str | None = None, *, setup: bool = False) -> Iterator[Any]:
    from langgraph.checkpoint.postgres import PostgresSaver

    url = database_url or get_settings().DATABASE_URL
    if not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("Invalid PostgreSQL connection string for LangGraph checkpointer")
    with PostgresSaver.from_conn_string(url) as checkpointer:
        if setup:
            checkpointer.setup()
        yield checkpointer
