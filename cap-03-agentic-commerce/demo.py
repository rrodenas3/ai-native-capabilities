"""Cap-03 Sparky demo."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cap03_loader import load_attr  # noqa: E402

build_graph = load_attr("cap03_sparky", "agents/sparky_graph.py", "build_graph")
initial_state = load_attr("cap03_sparky", "agents/sparky_graph.py", "initial_state")
SessionStore = load_attr("cap03_session_store", "memory/session_store.py", "SessionStore")


def main() -> None:
    console = Console()
    graph = build_graph()
    store = SessionStore()
    messages = [
        "I need a coffee gift recommendation",
        "Where is order 1001 and can I return it?",
        "This is the third time, I want a human manager now",
    ]
    for index, message in enumerate(messages, start=1):
        state = initial_state(message, session_id=f"demo-{index}", customer_id="cust-1")
        state["session_store"] = store
        state["memory_opt_in"] = True
        output = graph.invoke(state, config={"configurable": {"thread_id": f"demo-{index}"}})
        console.print(f"[bold]Message:[/] {message}")
        console.print(f"Intent: {output.get('intent_class')} | Outcome: {output.get('session_outcome')}")
        if output.get("recommendations"):
            console.print(f"Top recommendation: {output['recommendations'][0].product.name}")
        if output.get("resolution"):
            console.print(output["resolution"].resolution_text)
        if output.get("escalation_triggered"):
            console.print(f"Escalated to {output.get('human_agent_id')}: {output.get('escalation_reason')}")


if __name__ == "__main__":
    main()
