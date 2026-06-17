"""Schemas for Cap-03 commerce agents."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IntentClass(StrEnum):
    DISCOVERY = "DISCOVERY"
    REORDER = "REORDER"
    SUPPORT = "SUPPORT"
    COMPLAINT = "COMPLAINT"
    ESCALATION = "ESCALATION"
    BROWSE = "BROWSE"
    COMPARISON = "COMPARISON"
    CLARIFICATION = "CLARIFICATION"


class ResolutionType(StrEnum):
    INFORMATION = "INFORMATION"
    ACTION_TAKEN = "ACTION_TAKEN"
    ESCALATED = "ESCALATED"


class ComplexityTier(StrEnum):
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"


class IntentResult(BaseModel):
    intent_class: IntentClass
    intent_confidence: float = Field(ge=0.0, le=1.0)
    sub_intent: str | None = None
    model: str = "claude-haiku-4-5-20251001"


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    cost: float
    stock: int
    tags: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    product: Product
    relevance_score: float = Field(ge=0.0, le=1.0)
    margin_score: float
    stock_score: float = Field(ge=0.0, le=1.0)
    combined_score: float
    rank: int


class SentimentResult(BaseModel):
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    frustration_flag: bool
    triggers: list[str] = Field(default_factory=list)
    model: str = "claude-haiku-4-5-20251001"


class ResolutionResult(BaseModel):
    resolution_type: ResolutionType
    resolution_text: str
    citations: list[str] = Field(default_factory=list)
    order_id: str | None = None


class EscalationResult(BaseModel):
    escalation_triggered: bool
    escalation_reason: str | None = None
    human_agent_id: str | None = None
    complexity_tier: ComplexityTier = ComplexityTier.SIMPLE


class SessionRecord(BaseModel):
    session_id: str
    customer_id: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    order_history: list[dict[str, Any]] = Field(default_factory=list)
    session_outcome: str | None = None
    opt_in: bool = False
    expires_at: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(days=30))
