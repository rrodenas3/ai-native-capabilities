"""Verification agent for Cap-01 citation accuracy enforcement."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from core.schemas import AgentHop, AgentHopType, AuditEvent, CapabilityID, RetrievalResult
from core.utils.settings import get_settings


class VerificationFlag(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim: str
    status: Literal["UNVERIFIED"] = "UNVERIFIED"
    reason: str


def verification_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    analysis_notes = str(state.get("analysis_notes", ""))
    retrieval_results = list(state.get("retrieval_results", []))
    claims = extract_claims(analysis_notes)
    flags = [
        VerificationFlag(claim=claim, reason="No supporting retrieved chunk found")
        for claim in claims
        if not _is_supported(claim, retrieval_results)
    ]
    supported = len(claims) - len(flags)
    citation_accuracy = supported / len(claims) if claims else 1.0

    hop = AgentHop(
        agent_name="verification",
        hop_type=AgentHopType.VERIFICATION,
        model=settings.LLM_POWERFUL,
        confidence=citation_accuracy,
    )
    audit_event = AuditEvent(
        capability=CapabilityID.DECISION_INTELLIGENCE,
        run_id=str(state.get("run_id", "")),
        session_id=str(state.get("session_id", "")),
        event_type="verification.completed",
        agent_name="verification",
        action="verify_claims",
        payload={
            "claim_count": len(claims),
            "unverified_count": len(flags),
            "citation_accuracy": citation_accuracy,
        },
    )
    existing_uncertainty = list(state.get("uncertainty_flags", []))
    return {
        **state,
        "current_agent": "verification",
        "verification_flags": flags,
        "citation_accuracy": citation_accuracy,
        "uncertainty_flags": [
            *existing_uncertainty,
            *[f"UNVERIFIED: {flag.claim}" for flag in flags],
        ],
        "agent_hops": [*state.get("agent_hops", []), hop],
        "audit_trail": [*state.get("audit_trail", []), audit_event],
    }


def extract_claims(analysis_notes: str) -> list[str]:
    candidates = re.split(r"(?<=[.!?])\s+|\n+", analysis_notes)
    claims = []
    for candidate in candidates:
        cleaned = candidate.strip(" -")
        if not cleaned or ":" in cleaned[:24]:
            continue
        if len(cleaned.split()) >= 4:
            claims.append(cleaned.rstrip("."))
    return claims


def _is_supported(claim: str, retrieval_results: list[RetrievalResult]) -> bool:
    claim_terms = _meaningful_terms(claim)
    if not claim_terms:
        return True
    for result in retrieval_results:
        content_terms = _meaningful_terms(result.chunk.content)
        overlap = claim_terms & content_terms
        if len(overlap) / len(claim_terms) >= 0.6:
            return True
    return False


def _meaningful_terms(text: str) -> set[str]:
    return {
        token.strip(".,;:()[]").lower()
        for token in text.split()
        if len(token.strip(".,;:()[]")) > 4
    }

