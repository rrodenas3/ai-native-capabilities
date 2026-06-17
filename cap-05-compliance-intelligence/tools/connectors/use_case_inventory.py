"""In-memory connector for the internal AI use-case inventory."""

from __future__ import annotations

from typing import Any


class UseCaseInventory:
    def __init__(self, use_cases: list[dict[str, Any]] | None = None) -> None:
        self._use_cases = {item["id"]: dict(item) for item in (use_cases or default_use_cases())}

    def list_use_cases(self) -> list[dict[str, Any]]:
        return list(self._use_cases.values())

    def get_use_case(self, use_case_id: str) -> dict[str, Any]:
        return dict(self._use_cases[use_case_id])

    def add_use_case(self, use_case: dict[str, Any]) -> dict[str, Any]:
        self._use_cases[str(use_case["id"])] = dict(use_case)
        return dict(use_case)

    def update_coverage(self, use_case_id: str, obligation_id: str, status: str, evidence: str) -> dict[str, Any]:
        use_case = self._use_cases[use_case_id]
        coverage = dict(use_case.get("coverage", {}))
        coverage[obligation_id] = {"status": status, "evidence": evidence}
        use_case["coverage"] = coverage
        return dict(use_case)


def default_use_cases() -> list[dict[str, Any]]:
    return [
        {
            "id": "uc-employment-screening",
            "name": "Employment screening assistant",
            "description": "Ranks candidates for EU hiring workflows.",
            "owner": "people-ops",
            "ai_system_type": "employment",
            "risk_tier": "HIGH_RISK",
            "deployment_status": "production",
            "jurisdiction": "EU",
            "controls": ("risk_management", "logging", "human_oversight"),
        },
        {
            "id": "uc-support-chatbot",
            "name": "Customer support chatbot",
            "description": "Conversational assistant for EU customers.",
            "owner": "support",
            "ai_system_type": "transparency",
            "risk_tier": "LIMITED",
            "deployment_status": "production",
            "jurisdiction": "EU",
            "controls": ("ai_disclosure",),
        },
        {
            "id": "uc-gpai-platform",
            "name": "General-purpose model platform",
            "description": "Internal GPAI foundation model service.",
            "owner": "ml-platform",
            "ai_system_type": "general_purpose_ai",
            "risk_tier": "GPAI",
            "deployment_status": "pilot",
            "jurisdiction": "EU",
            "controls": ("technical_documentation",),
        },
    ]
