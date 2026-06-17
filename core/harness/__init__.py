"""Harness package — canonical loop, memory governance, sensors, golden principles."""

from core.harness.golden_principles import GoldenPrinciplesReport, run_all as run_golden_principles
from core.harness.loop import (
    ConsultationRequestPack,
    LoopState,
    LoopStopCondition,
    ToolRiskTier,
    get_tool_risk,
    register_tool_risk,
)

__all__ = [
    "ConsultationRequestPack",
    "GoldenPrinciplesReport",
    "LoopState",
    "LoopStopCondition",
    "ToolRiskTier",
    "get_tool_risk",
    "register_tool_risk",
    "run_golden_principles",
]


def __getattr__(name: str):
    """Lazy import sensors to avoid circular imports from memory module."""
    if name in {"SensorRegistry", "UnknownSensorError", "default_registry"}:
        from core.harness import sensors as _sensors

        return getattr(_sensors, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
