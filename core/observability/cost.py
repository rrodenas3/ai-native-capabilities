"""LLM cost telemetry."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

MODEL_PRICING = {
    "claude-opus-4-8": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gpt-5.5": {"input": 10.00, "output": 30.00},
    "gpt-5": {"input": 5.00, "output": 20.00},
    "gpt-5-mini": {"input": 0.40, "output": 1.60},
}

BudgetAlertHandler = Callable[[str, float, float], None]


@dataclass(slots=True)
class CostEvent:
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    agent_name: str
    run_id: str
    cost_usd: float


class CostTelemetry:
    """Record and aggregate token costs by run."""

    def __init__(
        self,
        *,
        pricing: dict[str, dict[str, float]] | None = None,
        budget_alert_handler: BudgetAlertHandler | None = None,
        session_budget_usd: float | None = None,
    ) -> None:
        self.pricing = pricing or MODEL_PRICING
        self.events: list[CostEvent] = []
        self.budget_alert_handler = budget_alert_handler
        self.session_budget_usd = session_budget_usd or float(os.getenv("SESSION_BUDGET_USD", "5.00"))

    def record_llm_call(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
        agent_name: str,
        run_id: str,
    ) -> CostEvent:
        cost_usd = self.calculate_cost(model, tokens_in, tokens_out)
        event = CostEvent(
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            agent_name=agent_name,
            run_id=run_id,
            cost_usd=cost_usd,
        )
        self.events.append(event)
        self.alert_budget_exceeded(run_id, self.session_budget_usd * 0.8)
        return event

    def calculate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        if model not in self.pricing:
            raise ValueError(f"Unknown model pricing for '{model}'")
        rates = self.pricing[model]
        return round(
            (tokens_in / 1_000_000) * rates["input"]
            + (tokens_out / 1_000_000) * rates["output"],
            8,
        )

    def get_run_cost(self, run_id: str) -> float:
        return round(sum(event.cost_usd for event in self.events if event.run_id == run_id), 8)

    def alert_budget_exceeded(self, run_id: str, threshold_usd: float) -> None:
        cost = self.get_run_cost(run_id)
        if cost >= threshold_usd and self.budget_alert_handler is not None:
            self.budget_alert_handler(run_id, cost, threshold_usd)

