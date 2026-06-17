"""Common metric implementations for capability evals."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from statistics import mean
from typing import ClassVar

from pydantic import BaseModel, Field

COMMON_METRICS = [
    "task_success_rate",
    "human_override_rate",
    "cost_per_task_usd",
    "response_latency_p95_ms",
    "hallucination_rate",
]

HallucinationJudge = Callable[["AgentResult"], bool]


@dataclass(slots=True)
class AgentResult:
    success: bool
    human_overridden: bool = False
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    output: str = ""
    grounded: bool = True


@dataclass(slots=True)
class TestCase:
    __test__: ClassVar[bool] = False

    case_id: str
    result: AgentResult


class CommonMetrics(BaseModel):
    task_success_rate: float = Field(ge=0.0, le=1.0)
    human_override_rate: float = Field(ge=0.0, le=1.0)
    cost_per_task_usd: float = Field(ge=0.0)
    response_latency_p95_ms: float = Field(ge=0.0)
    hallucination_rate: float = Field(ge=0.0, le=1.0)


def task_success_rate(results: list[AgentResult]) -> float:
    if not results:
        return 0.0
    return sum(result.success for result in results) / len(results)


def human_override_rate(results: list[AgentResult]) -> float:
    if not results:
        return 0.0
    return sum(result.human_overridden for result in results) / len(results)


def cost_per_task_usd(results: list[AgentResult]) -> float:
    if not results:
        return 0.0
    return mean(result.cost_usd for result in results)


def response_latency_p95_ms(results: list[AgentResult]) -> float:
    if not results:
        return 0.0
    values = sorted(result.latency_ms for result in results)
    index = max(round(0.95 * len(values)) - 1, 0)
    return values[index]


def hallucination_rate(
    results: list[AgentResult],
    judge: HallucinationJudge | None = None,
) -> float:
    """Estimate ungrounded-output rate.

    In CI/mock mode the LLM-as-judge path is deterministic and free. Real LLM
    judging is injected later via ``judge`` so this core package does not
    hardcode model providers or model names.
    """

    if not results:
        return 0.0
    if os.getenv("LLM_MODE", "mock") == "mock" and judge is None:
        return 0.0
    judgments = [judge(result) if judge else not result.grounded for result in results]
    return sum(judgments) / len(judgments)


def compute_common_metrics(
    results: list[AgentResult],
    judge: HallucinationJudge | None = None,
) -> CommonMetrics:
    return CommonMetrics(
        task_success_rate=task_success_rate(results),
        human_override_rate=human_override_rate(results),
        cost_per_task_usd=cost_per_task_usd(results),
        response_latency_p95_ms=response_latency_p95_ms(results),
        hallucination_rate=hallucination_rate(results, judge),
    )
