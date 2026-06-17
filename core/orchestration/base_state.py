"""Base LangGraph state shared by every capability graph."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from langchain_core.messages import BaseMessage

from core.schemas.base import AgentHop, AuditEvent


class BaseAgentState(TypedDict):
    """State contract every capability extends.

    LangGraph state must remain JSON-serialisable once checkpointing is enabled.
    Capability-specific states should subclass this TypedDict and add their own
    fields without changing these shared keys.
    """

    run_id: str
    session_id: str
    capability_id: str
    messages: list[BaseMessage]
    current_agent: str
    agent_hops: list[AgentHop]
    error_state: str | None
    human_approved: bool | None
    audit_trail: list[AuditEvent]
    cost_tokens: int
    latency_ms: float

    human_gate_payload: NotRequired[dict[str, Any]]
    eval_metrics: NotRequired[list[str]]
    cost_telemetry: NotRequired[dict[str, Any]]

