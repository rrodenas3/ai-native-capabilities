"""Reusable LangGraph builder for capability implementations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from core.orchestration.base_state import BaseAgentState
from core.schemas.base import AgentHop

StateUpdate = dict[str, Any]
StateNode = Callable[[BaseAgentState], StateUpdate | BaseAgentState]
ThresholdFn = Callable[[BaseAgentState], bool]


class BaseCapabilityGraph:
    """Base graph with shared human-gate, eval, and cost telemetry nodes."""

    def __init__(
        self,
        capability_id: str,
        state_schema: type = BaseAgentState,
    ) -> None:
        self.capability_id = capability_id
        self.state_schema = state_schema
        self.graph = StateGraph(state_schema)
        self._entry_node: str | None = None
        self._terminal_nodes: set[str] = set()
        self._compiled: CompiledStateGraph | None = None

    def add_node(self, name: str, node: StateNode, *, terminal: bool = False) -> None:
        """Add a node and optionally mark it as a terminal domain node."""

        self._ensure_not_compiled()
        self.graph.add_node(name, node)
        if self._entry_node is None:
            self._entry_node = name
            self.graph.add_edge(START, name)
        if terminal:
            self._terminal_nodes.add(name)

    def add_edge(self, start_key: str, end_key: str) -> None:
        """Add a graph edge."""

        self._ensure_not_compiled()
        self.graph.add_edge(start_key, end_key)

    def build(self) -> CompiledStateGraph:
        """Compile the graph and return a LangGraph CompiledStateGraph."""

        self._ensure_not_compiled()
        if self._entry_node is None:
            self.add_node("start", self._start_node, terminal=True)

        for node_name in self._terminal_nodes or {self._entry_node}:
            self.graph.add_edge(node_name, END)

        self._compiled = self.graph.compile()
        return self._compiled

    def add_human_gate(self, node_name: str, threshold_fn: ThresholdFn) -> str:
        """Add a LangGraph interrupt gate after ``node_name``.

        The gate interrupts only when ``threshold_fn`` returns true and the state
        has not already recorded human approval.
        """

        self._ensure_not_compiled()
        gate_name = f"{node_name}_human_gate"

        def human_gate(state: BaseAgentState) -> StateUpdate:
            requires_approval = threshold_fn(state)
            if not requires_approval:
                return {"human_approved": state.get("human_approved")}
            if state.get("human_approved") is True:
                return {"human_approved": True}

            payload = {
                "capability_id": state.get("capability_id", self.capability_id),
                "run_id": state.get("run_id"),
                "session_id": state.get("session_id"),
                "current_agent": state.get("current_agent"),
                "reason": "human approval required",
            }
            decision = interrupt(payload)
            if isinstance(decision, dict):
                return {
                    "human_approved": bool(decision.get("approved", False)),
                    "human_gate_payload": decision,
                }
            return {"human_approved": bool(decision), "human_gate_payload": {"decision": decision}}

        self.graph.add_node(gate_name, human_gate)
        self.graph.add_edge(node_name, gate_name)
        self._terminal_nodes.discard(node_name)
        self._terminal_nodes.add(gate_name)
        return gate_name

    def add_eval_node(self, metrics: list[str]) -> str:
        """Add a shared eval marker node.

        Capability-specific eval execution is implemented later in
        ``core/evals``. This node records which metrics the graph must emit.
        """

        self._ensure_not_compiled()
        node_name = "eval"

        def eval_node(state: BaseAgentState) -> StateUpdate:
            return {"eval_metrics": list(metrics)}

        self.graph.add_node(node_name, eval_node)
        if self._entry_node is not None:
            for terminal in list(self._terminal_nodes or {self._entry_node}):
                self.graph.add_edge(terminal, node_name)
                self._terminal_nodes.discard(terminal)
        else:
            self._entry_node = node_name
            self.graph.add_edge(START, node_name)
        self._terminal_nodes.add(node_name)
        return node_name

    def add_cost_telemetry(self) -> str:
        """Add a node that aggregates token and cost data from agent hops."""

        self._ensure_not_compiled()
        node_name = "cost_telemetry"

        def cost_node(state: BaseAgentState) -> StateUpdate:
            hops = state.get("agent_hops", [])
            tokens = state.get("cost_tokens", 0)
            cost_usd = 0.0
            for hop in hops:
                if isinstance(hop, AgentHop):
                    tokens += hop.tokens_in + hop.tokens_out
                    cost_usd += hop.cost_usd
                elif isinstance(hop, dict):
                    tokens += int(hop.get("tokens_in", 0)) + int(hop.get("tokens_out", 0))
                    cost_usd += float(hop.get("cost_usd", 0.0))

            return {
                "cost_tokens": tokens,
                "cost_telemetry": {
                    "tokens": tokens,
                    "cost_usd": round(cost_usd, 6),
                    "run_id": state.get("run_id"),
                },
            }

        self.graph.add_node(node_name, cost_node)
        if self._entry_node is not None:
            for terminal in list(self._terminal_nodes or {self._entry_node}):
                self.graph.add_edge(terminal, node_name)
                self._terminal_nodes.discard(terminal)
        else:
            self._entry_node = node_name
            self.graph.add_edge(START, node_name)
        self._terminal_nodes.add(node_name)
        return node_name

    @staticmethod
    def _start_node(state: BaseAgentState) -> StateUpdate:
        return {
            "capability_id": state.get("capability_id"),
            "current_agent": state.get("current_agent", "start"),
        }

    def _ensure_not_compiled(self) -> None:
        if self._compiled is not None:
            raise RuntimeError("Graph has already been compiled")

