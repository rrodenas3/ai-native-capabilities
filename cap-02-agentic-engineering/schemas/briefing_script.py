"""Pydantic schemas for Cap-02 SASE artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BriefingStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ARCHIVED = "ARCHIVED"


class Complexity(StrEnum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


class CriteriaStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


class GoalAndWhy(BaseModel):
    goal: str = Field(min_length=1)
    why: str = Field(min_length=1)
    business_value: str = Field(min_length=1)


class AcceptanceCriterion(BaseModel):
    id: str = Field(pattern=r"^AC-\d{2,}$")
    description: str = Field(min_length=1)
    testable: bool = True
    test_command: str | None = None


class WhatAndSuccess(BaseModel):
    scope: str = Field(min_length=1)
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)
    invariants: list[str] = Field(default_factory=list)
    anti_goals: list[str] = Field(default_factory=list)


class NeededContext(BaseModel):
    architecture_refs: list[str] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    patterns_to_follow: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class ImplementationTask(BaseModel):
    id: str = Field(pattern=r"^TASK-\d{2,}$")
    description: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    estimated_complexity: Complexity


class BriefingScript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    briefing_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    status: BriefingStatus
    author: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    created_at: datetime
    goal_and_why: GoalAndWhy
    what_and_success: WhatAndSuccess
    all_needed_context: NeededContext
    implementation_tasks: list[ImplementationTask] = Field(min_length=1)
    failure_modes: list[str] = Field(default_factory=list)
    codex_instructions: str = Field(min_length=1)

    @field_validator("created_at", mode="before")
    @classmethod
    def _parse_created_at(cls, value: Any) -> Any:
        if isinstance(value, str) and value.endswith("Z"):
            return value[:-1] + "+00:00"
        return value

    @property
    def briefing_completeness(self) -> float:
        required = [
            self.goal_and_why,
            self.what_and_success,
            self.all_needed_context,
            self.implementation_tasks,
            self.codex_instructions,
        ]
        return 1.0 if all(required) else 0.0


class SecurityScan(BaseModel):
    tool: str = "bandit+semgrep"
    critical: int = Field(ge=0)
    high: int = Field(ge=0)
    medium: int = Field(ge=0)
    low: int = Field(ge=0)
    findings: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.critical > 0


class CriteriaScore(BaseModel):
    id: str
    status: CriteriaStatus
    evidence: str = Field(min_length=1)


class MergeReadinessPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    briefing_id: str
    pack_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    agent: str
    files_changed: list[str]
    tests_added: list[str]
    coverage_pct: float = Field(ge=0.0, le=1.0)
    security_scan: SecurityScan
    criteria_scores: list[CriteriaScore]
    crps_raised: list[dict[str, Any]] = Field(default_factory=list)
    crps_resolved: list[dict[str, Any]] = Field(default_factory=list)
    agent_notes: str
    ready: bool = False

    @field_validator("ready")
    @classmethod
    def _ready_requires_no_critical(cls, value: bool, info) -> bool:
        security_scan = info.data.get("security_scan")
        if value and security_scan is not None and security_scan.critical > 0:
            raise ValueError("MergeReadinessPack cannot be ready with critical security findings")
        return value


def minimal_valid_briefing(**overrides: Any) -> BriefingScript:
    data: dict[str, Any] = {
        "briefing_id": "BRIEF-20260617-demo",
        "version": 1,
        "status": "APPROVED",
        "author": "agent-coach",
        "agent": "codex",
        "created_at": "2026-06-17T00:00:00Z",
        "goal_and_why": {
            "goal": "Add a deterministic utility.",
            "why": "Demonstrate the SASE loop.",
            "business_value": "Improves repeatable agent execution.",
        },
        "what_and_success": {
            "scope": "Create one small module and test.",
            "acceptance_criteria": [
                {
                    "id": "AC-01",
                    "description": "Generated code includes runnable tests.",
                    "testable": True,
                    "test_command": "pytest",
                }
            ],
            "invariants": [],
            "anti_goals": [],
        },
        "all_needed_context": {
            "architecture_refs": [],
            "relevant_files": [],
            "patterns_to_follow": [],
            "constraints": ["Do not commit directly to main."],
        },
        "implementation_tasks": [
            {
                "id": "TASK-01",
                "description": "Implement the utility.",
                "depends_on": [],
                "estimated_complexity": "S",
            }
        ],
        "failure_modes": [],
        "codex_instructions": "Work on a branch, run tests, and raise CRP when blocked.",
    }
    data.update(overrides)
    return BriefingScript.model_validate(data)
