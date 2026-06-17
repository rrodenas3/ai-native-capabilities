"""Structured output schema for Cap-01 decision briefs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.schemas import Finding


class BriefOutput(BaseModel):
    """Board-ready decision intelligence brief."""

    model_config = ConfigDict(frozen=True)

    executive_summary: str = Field(min_length=1)
    key_findings: list[Finding] = Field(min_length=1)
    uncertainty_flags: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(min_length=3, max_length=5)
    overall_confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("key_findings")
    @classmethod
    def _require_citations(cls, findings: list[Finding]) -> list[Finding]:
        missing = [finding.claim for finding in findings if not finding.citations]
        if missing:
            raise ValueError("Every finding must include at least one citation")
        return findings
