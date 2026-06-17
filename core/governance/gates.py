"""Five-gate governance engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.schemas.base import GateResult

GateOutcome = Literal["PROCEED", "HOLD", "REJECT"]

GATE_DEFINITIONS: dict[str, dict[str, object]] = {
    "gate_1_use_case": {
        "number": 1,
        "question": "Is this task worth automating or augmenting?",
        "criteria": ["high_frequency", "high_friction", "addressable_data", "clear_kpi"],
    },
    "gate_2_data": {
        "number": 2,
        "question": "Can the system see the right data safely?",
        "criteria": [
            "permissions_mapped",
            "provenance_visible",
            "red_data_excluded",
            "privacy_assessed",
        ],
    },
    "gate_3_action": {
        "number": 3,
        "question": "Can the agent act safely?",
        "criteria": [
            "tool_contracts_defined",
            "rollback_path_exists",
            "approval_rules_set",
            "escalation_tree_defined",
        ],
    },
    "gate_4_quality": {
        "number": 4,
        "question": "Is performance better than status quo?",
        "criteria": [
            "eval_pass_rate",
            "hallucination_within_budget",
            "latency_within_budget",
            "cost_within_budget",
        ],
    },
    "gate_5_scale": {
        "number": 5,
        "question": "Can it operate reliably in production?",
        "criteria": [
            "monitoring_live",
            "incident_response_defined",
            "rollback_tested",
            "cost_controls_set",
        ],
    },
}


@dataclass(slots=True)
class GovernanceGateEngine:
    """Evaluate spec-defined governance gates."""

    eval_pass_threshold: float = 0.85

    def evaluate(self, gate_name: str, criteria: dict[str, bool | float]) -> GateResult:
        definition = self._definition(gate_name)
        required = definition["criteria"]
        assert isinstance(required, list)
        criteria_results = {
            criterion: self._criterion_passes(criterion, criteria.get(criterion, False))
            for criterion in required
        }
        missing = [criterion for criterion in required if criterion not in criteria]
        passed = all(criteria_results.values()) and not missing
        notes = f"Missing criteria: {', '.join(missing)}" if missing else None
        return GateResult(
            gate_number=int(definition["number"]),
            gate_name=gate_name,
            passed=passed,
            criteria_results=criteria_results,
            notes=notes,
        )

    def evaluate_all(self, criteria_by_gate: dict[str, dict[str, bool | float]]) -> list[GateResult]:
        return [
            self.evaluate(gate_name, criteria_by_gate.get(gate_name, {}))
            for gate_name in GATE_DEFINITIONS
        ]

    def outcome(self, result: GateResult) -> GateOutcome:
        if result.passed:
            return "PROCEED"
        if result.notes:
            return "HOLD"
        return "REJECT"

    def _criterion_passes(self, criterion: str, value: bool | float) -> bool:
        if criterion == "eval_pass_rate":
            return float(value) >= self.eval_pass_threshold
        return bool(value)

    @staticmethod
    def _definition(gate_name: str) -> dict[str, object]:
        try:
            return GATE_DEFINITIONS[gate_name]
        except KeyError as exc:
            raise KeyError(f"Unknown governance gate '{gate_name}'") from exc

