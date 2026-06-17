"""Structured schema contracts for Cap-05 compliance intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

DocumentType = Literal["REGULATION", "AMENDMENT", "GUIDANCE", "ENFORCEMENT"]
ObligationType = Literal["PROHIBITED", "HIGH_RISK", "TRANSPARENCY", "GENERAL", "GPAI"]
ReviewDecision = Literal["CONFIRM", "MODIFY", "REJECT", "ESCALATE"]
CoverageStatus = Literal["COVERED", "GAP", "PARTIAL", "EXEMPT"]


@dataclass(frozen=True)
class Regulation:
    id: str
    name: str
    jurisdiction: str
    issuer: str
    publication_date: str
    effective_date: str
    url: str


@dataclass(frozen=True)
class Article:
    id: str
    regulation_id: str
    number: str
    title: str
    text: str
    last_amended: str | None = None


@dataclass(frozen=True)
class Obligation:
    id: str
    article_id: str
    obligation_type: ObligationType
    subject: str
    action_required: str
    effective_date: str
    deadline_type: str
    penalty_max_eur: float | None
    penalty_pct_revenue: float | None
    confidence: float
    article_reference: str
    anchor_text: str
    jurisdiction: str
    source_url: str
    expert_confirmed: bool = False
    confirmed_by: str | None = None
    confirmed_at: str | None = None
    status: str = "PENDING"
    valid_from: str | None = None
    valid_until: str | None = None
    requires_expert_review: bool = True
    extraction_model: str = "claude-opus-4-8"

    def confirmed(self, reviewer_id: str, decision_time: datetime | None = None) -> Obligation:
        timestamp = (decision_time or datetime.now(UTC)).isoformat()
        return Obligation(
            id=self.id,
            article_id=self.article_id,
            obligation_type=self.obligation_type,
            subject=self.subject,
            action_required=self.action_required,
            effective_date=self.effective_date,
            deadline_type=self.deadline_type,
            penalty_max_eur=self.penalty_max_eur,
            penalty_pct_revenue=self.penalty_pct_revenue,
            confidence=self.confidence,
            article_reference=self.article_reference,
            anchor_text=self.anchor_text,
            jurisdiction=self.jurisdiction,
            source_url=self.source_url,
            expert_confirmed=True,
            confirmed_by=reviewer_id,
            confirmed_at=timestamp,
            status="CONFIRMED",
            valid_from=self.valid_from or self.effective_date,
            valid_until=self.valid_until,
            requires_expert_review=False,
            extraction_model=self.extraction_model,
        )


@dataclass(frozen=True)
class UseCase:
    id: str
    name: str
    description: str
    owner: str
    ai_system_type: str
    risk_tier: str
    deployment_status: str
    jurisdiction: str = "EU"
    controls: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Coverage:
    use_case_id: str
    obligation_id: str
    status: CoverageStatus
    evidence: str
    owner: str
    deadline: str


@dataclass(frozen=True)
class GapReport:
    id: str
    use_case_id: str
    obligation_id: str
    severity: str
    deadline: str
    assigned_to: str
    status: str
    reason: str
