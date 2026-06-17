"""
core/schemas/base.py
Shared Pydantic models and TypedDicts used across all 5 capabilities.
This file is the canonical type contract — Codex implements against this.

June 2026 — verified against LangGraph 1.0.5 state management conventions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────


class CapabilityID(str, Enum):
    DECISION_INTELLIGENCE = "cap-01"
    AGENTIC_ENGINEERING = "cap-02"
    AGENTIC_COMMERCE = "cap-03"
    AUTONOMOUS_OPERATIONS = "cap-04"
    COMPLIANCE_INTELLIGENCE = "cap-05"


class AgentHopType(str, Enum):
    SUPERVISOR = "supervisor"
    RETRIEVAL = "retrieval"
    ANALYSIS = "analysis"
    VERIFICATION = "verification"
    ASSEMBLY = "assembly"
    EXECUTION = "execution"
    SECURITY = "security"
    HUMAN_GATE = "human_gate"
    EXCEPTION = "exception"
    ESCALATION = "escalation"


class HumanGateStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    MODIFIED = "modified"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


class EvidenceGrade(str, Enum):
    """Evidence quality grade used in all capability docs."""
    MEASURED = "M"       # Independent, quantified, peer-reviewed or audited
    PARTIAL = "P"        # Company-reported, directionally credible, not independently verified
    VENDOR = "V"         # Treat as directional only; self-interested source


class RiskTier(str, Enum):
    """EU AI Act risk classification."""
    PROHIBITED = "prohibited"
    HIGH_RISK = "high_risk"
    TRANSPARENCY = "transparency"
    GENERAL = "general"
    GPAI = "gpai"


# ── Core shared schemas ─────────────────────────────────────────────────────────


class AgentHop(BaseModel):
    """Records a single agent invocation — logged to OTEL and audit trail."""

    hop_id: UUID = Field(default_factory=uuid4)
    agent_name: str
    hop_type: AgentHopType
    model: str                          # exact API string, e.g. "claude-sonnet-4-6"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    confidence: float | None = None     # 0.0–1.0; None if not applicable
    success: bool = True
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditEvent(BaseModel):
    """Immutable audit event — written to append-only audit_trail table."""

    event_id: UUID = Field(default_factory=uuid4)
    capability: CapabilityID
    run_id: str
    session_id: str
    event_type: str                     # e.g. "human_gate.approved", "po.created"
    agent_name: str | None = None
    action: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    decision: str | None = None         # human decision text
    approved_by: str | None = None
    cost_usd: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryEvent(BaseModel):
    """Episodic memory entry — stored in PostgreSQL + pgvector."""

    event_id: UUID = Field(default_factory=uuid4)
    capability: CapabilityID
    session_id: str
    run_id: str | None = None
    event_type: str
    content: str                        # text content for embedding
    embedding: list[float] | None = None  # 1536-dim for text-embedding-3-large
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentChunk(BaseModel):
    """A chunk of an indexed document — used in semantic memory."""

    chunk_id: UUID = Field(default_factory=uuid4)
    capability: CapabilityID
    doc_id: str
    chunk_index: int
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    access_tier: Literal["public", "internal", "restricted"] = "internal"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RetrievalResult(BaseModel):
    """A single retrieval result from hybrid search."""

    chunk: DocumentChunk
    semantic_score: float               # cosine similarity
    lexical_score: float | None = None  # BM25 score
    combined_score: float               # weighted combination
    rank: int


class Citation(BaseModel):
    """A verifiable source citation — every factual claim must have one."""

    citation_id: UUID = Field(default_factory=uuid4)
    source_doc_id: str
    source_title: str
    source_date: str | None = None
    chunk_index: int
    excerpt: str                        # the exact text supporting the claim
    confidence: float                   # 0.0–1.0
    access_tier: str = "internal"


class Finding(BaseModel):
    """A key finding in a decision brief — claim + citation + confidence."""

    finding_id: UUID = Field(default_factory=uuid4)
    claim: str                          # the factual statement
    citations: list[Citation]           # must have at least one
    confidence: float                   # overall confidence in this finding
    uncertainty_note: str | None = None # explicit uncertainty flag if confidence < 0.7


# ── Base LangGraph state ────────────────────────────────────────────────────────


class BaseAgentState:
    """
    Base TypedDict for all 5 capability LangGraph state graphs.
    Each capability extends this with capability-specific fields.

    Usage:
        from typing import TypedDict
        from core.schemas.base import BaseAgentState

        class DecisionBriefState(TypedDict, total=False):
            # Inherit all base fields by reference
            run_id: str
            session_id: str
            capability_id: str
            ...your fields...

    Note: LangGraph 1.0.5 uses TypedDict for state, not Pydantic models.
    Pydantic models are used for nested data structures within state.
    """

    # Required on every state
    run_id: str
    session_id: str
    capability_id: str          # CapabilityID value

    # Orchestration
    current_agent: str
    agent_hops: list[dict]      # serialised AgentHop dicts (must be JSON-serialisable)
    error_state: str | None

    # Governance
    human_approved: bool | None
    human_gate_status: str | None  # HumanGateStatus value
    human_modifications: str | None

    # Audit
    audit_trail: list[dict]     # serialised AuditEvent dicts
    checkpoint_id: str | None

    # Cost tracking
    cost_tokens_in: int
    cost_tokens_out: int
    cost_usd_total: float

    # Timing
    started_at: str             # ISO 8601
    latency_ms_total: float


# ── Eval schemas ────────────────────────────────────────────────────────────────


class MetricResult(BaseModel):
    """Single metric result from an eval run."""

    name: str
    value: float
    threshold: float
    lower_is_better: bool
    passed: bool
    blocking: bool


class EvalReport(BaseModel):
    """Output of a capability eval suite run."""

    cap: str
    status: Literal["pass", "warn", "fail", "error", "no_eval_suite", "missing"]
    score: float                        # weighted aggregate of all metrics
    metrics: dict[str, float]           # raw metric values
    metric_results: list[MetricResult]
    blocking_failures: list[str]        # names of blocking metrics that failed
    total_cost_usd: float | None = None
    elapsed_s: float | None = None
    note: str | None = None
    stderr: str | None = None
    run_id: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── MCP connector schemas ───────────────────────────────────────────────────────


class MCPTool(BaseModel):
    """Definition of a tool exposed by an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool = True              # MCP tool annotation (spec 2025-11-25)


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server connection."""

    name: str
    transport: Literal["streamable-http", "stdio"] = "streamable-http"
    url: str | None = None              # required for streamable-http
    mock_mode: bool = False
    tools: list[str] = Field(default_factory=list)  # tool names this server exposes
    auth_required: bool = True          # OAuth 2.1 + PKCE for remote servers


# ── Governance schemas ──────────────────────────────────────────────────────────


class GateResult(BaseModel):
    """Result of a governance gate check."""

    gate_number: int                    # 1–5
    gate_name: str
    passed: bool
    criteria_results: dict[str, bool]
    notes: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GovernanceDecision(BaseModel):
    """A governance decision record — stored in audit trail."""

    decision_id: UUID = Field(default_factory=uuid4)
    capability: CapabilityID
    run_id: str
    decision_type: str                  # "human_gate", "governance_gate", "cost_alert"
    decided_by: str                     # human ID or "system"
    decision: HumanGateStatus
    rationale: str | None = None
    value_usd: float | None = None      # monetary value of the action being approved
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
