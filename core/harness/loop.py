"""
core/harness/loop.py
The canonical agentic loop — shared across all 5 capabilities.

Every agent in this repo implements this bounded loop:
  PLAN → ACT → OBSERVE → VERIFY → CORRECT

Research basis: ADR-002 Harness Engineering (June 2026)
  - OpenAI "Harness engineering: leveraging Codex in an agent-first world"
  - Microsoft Azure SRE Agent pattern (3-min MTTM from 40.5h human-only)
  - Agent = Model + Harness
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Risk taxonomy ──────────────────────────────────────────────────────────────

class ToolRiskTier(str, Enum):
    """
    Every tool call is classified before execution.
    Classification determines whether human approval is required.

    Permission matrix (configurable via settings):
        READ_ONLY:   auto-execute, log to OTEL
        IDEMPOTENT:  auto-execute, log + verify result
        FINANCIAL:   human gate if above AUTONOMOUS_ACTION_THRESHOLD_USD
        DESTRUCTIVE: always human gate, no exceptions
    """
    READ_ONLY    = "read_only"    # search, fetch, list, read
    IDEMPOTENT   = "idempotent"   # create-with-dedup, upsert, classify
    FINANCIAL    = "financial"    # PO generation, payment, budget changes
    DESTRUCTIVE  = "destructive"  # delete, send to external party, override


# Tool risk registry — populated by each capability's tool definitions
TOOL_RISK_REGISTRY: dict[str, ToolRiskTier] = {}


def register_tool_risk(tool_name: str, tier: ToolRiskTier) -> None:
    """Register a tool's risk tier. Call at capability initialization."""
    TOOL_RISK_REGISTRY[tool_name] = tier
    logger.debug(f"Tool registered: {tool_name} → {tier.value}")


def get_tool_risk(tool_name: str) -> ToolRiskTier:
    """Return the risk tier for a tool. Unknown tools default to DESTRUCTIVE."""
    return TOOL_RISK_REGISTRY.get(tool_name, ToolRiskTier.DESTRUCTIVE)


# ── Sensor architecture ────────────────────────────────────────────────────────

class SensorType(str, Enum):
    """
    Sensors run INSIDE the agent loop on every step.

    COMPUTATIONAL: deterministic, cheap, run every step.
      Examples: schema validation, permission check, budget check, citation presence.

    INFERENTIAL: LLM-as-judge, run selectively at quality gates.
      Examples: hallucination detection, security weakness scan, compliance check.
      CRITICAL: judge model MUST differ from the agent model family.
      Reason: prevents self-preference bias and prompt-injection of the judge.
    """
    COMPUTATIONAL = "computational"
    INFERENTIAL   = "inferential"


class SensorResult(BaseModel):
    sensor_name: str
    sensor_type: SensorType
    passed: bool
    score: float | None = None       # 0.0–1.0 for inferential sensors
    message: str | None = None
    blocking: bool = False           # if True and not passed → halt loop


class ComputationalSensor:
    """
    Base class for deterministic sensors.
    Subclass and implement `check(state) -> SensorResult`.
    """
    name: str = "base_computational_sensor"
    blocking: bool = False

    def check(self, state: dict[str, Any]) -> SensorResult:
        raise NotImplementedError


class InferentialSensor:
    """
    Base class for LLM-as-judge sensors (run at quality gates, not every step).
    Subclass and implement `check(state) -> SensorResult`.
    """
    name: str = "base_inferential_sensor"
    blocking: bool = False

    def check(self, state: dict[str, Any]) -> SensorResult:
        raise NotImplementedError


class SchemaSensor(ComputationalSensor):
    """Validates that a tool call matches the registered schema."""
    name = "schema_validation"
    blocking = True

    def __init__(self, schema: dict[str, Any]) -> None:
        self.schema = schema

    def check(self, tool_input: dict[str, Any]) -> SensorResult:
        # Implementation: validate tool_input against self.schema
        # Using jsonschema or pydantic model validation
        return SensorResult(
            sensor_name=self.name,
            sensor_type=SensorType.COMPUTATIONAL,
            passed=True,  # real impl validates here
            blocking=self.blocking,
        )


class BudgetSensor(ComputationalSensor):
    """Blocks execution if cost budget is at or above 80%."""
    name = "budget_check"
    blocking = True

    def __init__(self, budget_usd: float) -> None:
        self.budget_usd = budget_usd

    def check(self, current_cost_usd: float) -> SensorResult:
        ratio = current_cost_usd / self.budget_usd if self.budget_usd > 0 else 0.0
        passed = ratio < 0.80
        return SensorResult(
            sensor_name=self.name,
            sensor_type=SensorType.COMPUTATIONAL,
            passed=passed,
            score=1.0 - ratio,
            message=f"Budget: ${current_cost_usd:.4f} / ${self.budget_usd:.2f} ({ratio*100:.1f}%)",
            blocking=self.blocking,
        )


class CitationSensor(ComputationalSensor):
    """Verifies every Finding in a brief has at least one Citation."""
    name = "citation_presence"
    blocking = True

    def check(self, findings: list[dict]) -> SensorResult:
        missing = [f.get("finding_id", "?") for f in findings if not f.get("citations")]
        passed = len(missing) == 0
        return SensorResult(
            sensor_name=self.name,
            sensor_type=SensorType.COMPUTATIONAL,
            passed=passed,
            message=f"{len(missing)} finding(s) missing citations: {missing}" if missing else "All findings cited",
            blocking=self.blocking,
        )


# ── Canonical loop stop conditions ────────────────────────────────────────────

class LoopStopCondition(str, Enum):
    MAX_ITERATIONS     = "max_iterations"
    BUDGET_EXCEEDED    = "budget_exceeded"
    HUMAN_GATE_PENDING = "human_gate_pending"
    REPEATED_ERROR     = "repeated_error"       # same error 3× → CRP
    SENSOR_BLOCKED     = "sensor_blocked"       # blocking sensor failed
    TASK_COMPLETE      = "task_complete"
    CRP_RAISED         = "crp_raised"


class LoopState(BaseModel):
    """Tracks the canonical loop's runtime state."""
    iteration: int = 0
    max_iterations: int = 20             # from settings.MAX_LOOP_ITERATIONS
    cost_usd_total: float = 0.0
    session_budget_usd: float = 5.0      # from settings.SESSION_BUDGET_USD
    stop_condition: LoopStopCondition | None = None
    error_history: list[str] = Field(default_factory=list)
    crp_raised: bool = False
    sensors_passed: list[str] = Field(default_factory=list)
    sensors_failed: list[str] = Field(default_factory=list)

    def should_stop(self) -> bool:
        return self.stop_condition is not None

    def record_error(self, error: str) -> None:
        self.error_history.append(error)
        # Detect repeated identical error (3×) → CRP
        if self.error_history.count(error) >= 3:
            self.stop_condition = LoopStopCondition.REPEATED_ERROR
            self.crp_raised = True

    def tick(self) -> None:
        self.iteration += 1
        if self.iteration >= self.max_iterations:
            self.stop_condition = LoopStopCondition.MAX_ITERATIONS

    def check_budget(self) -> None:
        if self.cost_usd_total >= self.session_budget_usd * 0.80:
            self.stop_condition = LoopStopCondition.BUDGET_EXCEEDED


# ── CRP (Consultation Request Pack) ───────────────────────────────────────────

class ConsultationRequestPack(BaseModel):
    """
    When an agent is blocked, it raises a CRP rather than guessing.
    The CRP includes a proposed solution — not just the problem.
    Rule: raise CRP after 3 failed self-resolution attempts.
    """
    crp_id: str
    task_id: str
    capability: str
    iteration: int
    what_was_tried: list[str]
    what_failed: list[str]
    proposed_solution: str              # mandatory — agent must propose, not just describe
    proposed_solution_confidence: float # 0.0–1.0
    tradeoffs: str | None = None
    blocking: bool = True


# ── Golden Principles ──────────────────────────────────────────────────────────

"""
Golden principles live in each capability's `golden_principles.md`.
They are opinionated mechanical rules that agent-generated artifacts must follow.
The golden_principles_eval checks compliance on every generated artifact.

Format of golden_principles.md:
---
principle_id: GP-01
name: No hardcoded model strings
rule: Model strings must be read from settings, never hardcoded in agent code.
test: grep -r 'claude-' --include="*.py" | grep -v settings | grep -v test
severity: blocking
---

See: docs/adr/ADR-002-harness-engineering.md
"""
