"""Gap mapping between confirmed obligations and use-case controls."""

from __future__ import annotations

import hashlib
from typing import Any

CONTROL_KEYWORDS = {
    "HIGH_RISK": ("risk_management", "logging", "human_oversight", "technical_documentation"),
    "TRANSPARENCY": ("ai_disclosure", "transparency_notice"),
    "GPAI": ("technical_documentation", "copyright_policy", "model_evaluation"),
    "PROHIBITED": ("prohibited_practice_screening",),
    "GENERAL": ("governance_policy",),
}


def detect_gaps(confirmed_obligations: list[dict[str, Any]], use_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for obligation in confirmed_obligations:
        if obligation.get("expert_confirmed") is not True:
            continue
        for use_case in use_cases:
            if not _applies(obligation, use_case):
                continue
            missing = [control for control in _required_controls(obligation) if control not in set(use_case.get("controls", ()))]
            if not missing:
                continue
            gap_id = _gap_id(str(use_case["id"]), str(obligation["id"]))
            gaps.append(
                {
                    "id": gap_id,
                    "use_case_id": use_case["id"],
                    "obligation_id": obligation["id"],
                    "severity": _severity(obligation),
                    "deadline": obligation.get("effective_date", "UNKNOWN"),
                    "assigned_to": use_case.get("owner", "compliance"),
                    "status": "OPEN",
                    "reason": f"Missing controls: {', '.join(missing)}",
                }
            )
    return gaps


def write_gaps_to_graph(graph: Any, gaps: list[dict[str, Any]]) -> None:
    for gap in gaps:
        graph.add_node("GapReport", str(gap["id"]), gap)
        if gap["use_case_id"] in graph.nodes and gap["obligation_id"] in graph.nodes:
            graph.add_edge(str(gap["use_case_id"]), "HAS_GAP", str(gap["obligation_id"]), {"gap_id": gap["id"]})


def _applies(obligation: dict[str, Any], use_case: dict[str, Any]) -> bool:
    if obligation.get("jurisdiction", "EU") != use_case.get("jurisdiction", "EU"):
        return False
    obligation_type = obligation.get("obligation_type", "GENERAL")
    system_type = str(use_case.get("ai_system_type", "")).lower()
    anchor = str(obligation.get("anchor_text", "")).lower()
    if obligation_type == "HIGH_RISK":
        return use_case.get("risk_tier") == "HIGH_RISK" or system_type in anchor
    if obligation_type == "TRANSPARENCY":
        return "chatbot" in system_type or "transparency" in system_type or "interact" in anchor
    if obligation_type == "GPAI":
        return use_case.get("risk_tier") == "GPAI" or "general_purpose" in system_type
    if obligation_type == "PROHIBITED":
        return True
    return True


def _required_controls(obligation: dict[str, Any]) -> tuple[str, ...]:
    return CONTROL_KEYWORDS.get(str(obligation.get("obligation_type", "GENERAL")), CONTROL_KEYWORDS["GENERAL"])


def _severity(obligation: dict[str, Any]) -> str:
    if obligation.get("penalty_max_eur", 0) and float(obligation["penalty_max_eur"]) >= 35_000_000:
        return "CRITICAL"
    if obligation.get("obligation_type") in {"PROHIBITED", "HIGH_RISK"}:
        return "HIGH"
    return "MEDIUM"


def _gap_id(use_case_id: str, obligation_id: str) -> str:
    digest = hashlib.sha256(f"{use_case_id}|{obligation_id}".encode()).hexdigest()[:10]
    return f"gap-{digest}"
