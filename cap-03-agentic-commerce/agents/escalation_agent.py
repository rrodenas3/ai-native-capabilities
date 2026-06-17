"""Human escalation routing for Sparky."""

from __future__ import annotations

import re
from typing import Any

from cap03_schema_loader import ComplexityTier, EscalationResult


def should_escalate(state: dict[str, Any]) -> EscalationResult:
    message = str(state.get("raw_message", ""))
    if state.get("frustration_flag"):
        return EscalationResult(escalation_triggered=True, escalation_reason="frustration", human_agent_id="tier2-human", complexity_tier=ComplexityTier.COMPLEX)
    if re.search(r"\b(regulatory|legal|chargeback|payment dispute|human|representative|manager)\b", message, re.I):
        return EscalationResult(escalation_triggered=True, escalation_reason="mandatory_route", human_agent_id="tier2-human", complexity_tier=ComplexityTier.COMPLEX)
    if state.get("intent_class") in {"COMPLAINT", "ESCALATION"}:
        return EscalationResult(escalation_triggered=True, escalation_reason="intent", human_agent_id="tier2-human", complexity_tier=ComplexityTier.MEDIUM)
    return EscalationResult(escalation_triggered=False, complexity_tier=_tier(message))


def escalation_node(state: dict[str, Any]) -> dict[str, Any]:
    result = should_escalate(state)
    return {
        **state,
        "escalation_triggered": result.escalation_triggered,
        "escalation_reason": result.escalation_reason,
        "human_agent_id": result.human_agent_id,
        "complexity_tier": result.complexity_tier.value,
        "session_outcome": "escalated" if result.escalation_triggered else state.get("session_outcome"),
    }


def _tier(message: str) -> ComplexityTier:
    if len(message.split()) > 18:
        return ComplexityTier.MEDIUM
    return ComplexityTier.SIMPLE
