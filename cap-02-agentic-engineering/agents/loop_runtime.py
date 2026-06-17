"""LoopScript runtime for Cap-02 execution monitoring."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from core.harness.loop import ConsultationRequestPack, LoopState, LoopStopCondition
from core.harness.sensors import SensorRegistry, default_registry


class LoopRuntime:
    def __init__(self, max_iterations: int = 20, *, sensors: SensorRegistry | None = None) -> None:
        self.state = LoopState(max_iterations=max_iterations)
        self.progress_by_criterion: dict[str, bool] = {}
        self.sensors = sensors or default_registry()

    def record_step(
        self,
        criterion_id: str,
        accomplished: str,
        *,
        matched: bool,
        error: str | None = None,
    ) -> ConsultationRequestPack | None:
        self.state.tick()
        self.progress_by_criterion[criterion_id] = matched
        if error:
            self.state.record_error(error)
        if self.state.stop_condition in {LoopStopCondition.REPEATED_ERROR, LoopStopCondition.MAX_ITERATIONS}:
            return self.raise_crp(
                criterion_id,
                what_was_tried=[accomplished],
                what_failed=list(self.state.error_history) or ["Iteration budget exhausted"],
                proposed_solution="Ask the Agent Coach to clarify the blocked criterion or approve a narrower implementation.",
            )
        return None

    def raise_crp(
        self,
        task_id: str,
        *,
        what_was_tried: list[str],
        what_failed: list[str],
        proposed_solution: str,
        confidence: float = 0.72,
    ) -> ConsultationRequestPack:
        self.state.stop_condition = LoopStopCondition.CRP_RAISED
        self.state.crp_raised = True
        return ConsultationRequestPack(
            crp_id=f"CRP-{uuid4()}",
            task_id=task_id,
            capability="cap-02",
            iteration=self.state.iteration,
            what_was_tried=what_was_tried,
            what_failed=what_failed,
            proposed_solution=proposed_solution,
            proposed_solution_confidence=confidence,
            tradeoffs="Continuing without clarification risks brief drift.",
        )


def runtime_from_state(state: dict[str, Any]) -> LoopRuntime:
    max_iterations = int(state.get("max_iterations", 20))
    return LoopRuntime(max_iterations=max_iterations)
