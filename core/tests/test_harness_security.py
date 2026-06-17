"""Harness security and risk taxonomy tests (ADR-002)."""

from __future__ import annotations

from core.harness.loop import ToolRiskTier, get_tool_risk, register_tool_risk
from core.harness.sensors import default_registry


def test_unknown_tool_defaults_to_destructive() -> None:
    assert get_tool_risk("totally_unknown_tool_xyz") == ToolRiskTier.DESTRUCTIVE


def test_register_tool_risk() -> None:
    register_tool_risk("test_read_search", ToolRiskTier.READ_ONLY)
    assert get_tool_risk("test_read_search") == ToolRiskTier.READ_ONLY


def test_default_registry_runs_without_error() -> None:
    registry = default_registry()
    results = registry.run_computational(
        {
            "findings": [{"finding_id": "F-1", "citations": ["doc-1"]}],
            "current_cost_usd": 0.5,
        }
    )
    assert results
    assert registry.to_report(results)["harness_security_score"] >= 0.0
