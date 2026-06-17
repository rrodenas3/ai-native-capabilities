"""Cap-04 replenishment cycle demo."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from rich.console import Console

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cap04_loader import load_attr  # noqa: E402

build_graph = load_attr("cap04_graph", "agents/supply_chain_graph.py", "build_graph")
initial_state = load_attr("cap04_graph", "agents/supply_chain_graph.py", "initial_state")


def main() -> None:
    data_dir = ROOT / "tests" / "fixtures" / "data"
    sales = _read_csv(data_dir / "sales_history.csv")[:450]
    stock = _read_csv(data_dir / "stock_levels.csv")[:5]
    suppliers = _read_csv(data_dir / "supplier_catalog.csv")[:5]
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "cap04-demo"}}
    output = graph.invoke(initial_state(run_id="cap04-demo", sales_history=sales, stock_levels=stock, supplier_catalog=suppliers), config=config)
    if "__interrupt__" in output:
        output = graph.invoke(Command(resume={"status": "approved", "approver_id": "demo-user"}), config=config)
    console = Console()
    console.print(f"PO drafts: {len(output.get('po_drafts', []))}")
    console.print(f"Simulations: {len(output.get('simulation_results', []))}")
    console.print(f"ERP writes: {len(output.get('erp_writes', []))}")
    console.print(f"Approval status: {output.get('human_approval_status')}")


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    main()
