"""Audit-event schemas used by capability event trails."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from core.schemas.base import CapabilityID, HumanGateStatus


class AuditEventType(StrEnum):
    AGENT_HOP = "agent.hop"
    HUMAN_GATE = "human_gate.decision"
    TOOL_ACTION = "tool.action"
    COST_ALERT = "cost.alert"
    GOVERNANCE_GATE = "governance_gate.decision"


class CapabilityAuditEvent(BaseModel):
    """Immutable audit event envelope for capability-specific trails."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    capability: CapabilityID
    run_id: str
    session_id: str
    event_type: AuditEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HumanApprovalAuditEvent(CapabilityAuditEvent):
    event_type: AuditEventType = AuditEventType.HUMAN_GATE
    decision: HumanGateStatus
    approved_by: str | None = None


class ToolActionAuditEvent(CapabilityAuditEvent):
    event_type: AuditEventType = AuditEventType.TOOL_ACTION
    tool_name: str
    read_only: bool
    success: bool
