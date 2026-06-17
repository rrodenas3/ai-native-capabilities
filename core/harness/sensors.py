"""Sensor registry for the canonical agentic loop (ADR-002)."""

from __future__ import annotations

from typing import Any

from core.harness.loop import (
    ComputationalSensor,
    InferentialSensor,
    SensorResult,
    SensorType,
)


class UnknownSensorError(KeyError):
    """Raised when a sensor name is not registered."""


class SensorRegistry:
    """Register and run computational / inferential sensors by name."""

    def __init__(self) -> None:
        self._computational: dict[str, ComputationalSensor] = {}
        self._inferential: dict[str, InferentialSensor] = {}

    def register(self, sensor: ComputationalSensor | InferentialSensor) -> None:
        name = sensor.name
        if isinstance(sensor, ComputationalSensor):
            self._computational[name] = sensor
        else:
            self._inferential[name] = sensor

    def get(self, name: str) -> ComputationalSensor | InferentialSensor:
        if name in self._computational:
            return self._computational[name]
        if name in self._inferential:
            return self._inferential[name]
        raise UnknownSensorError(f"Unknown sensor: {name}")

    def run_computational(self, payload: dict[str, Any]) -> list[SensorResult]:
        results: list[SensorResult] = []
        for sensor in self._computational.values():
            if sensor.name == "budget_check":
                cost = float(payload.get("current_cost_usd", 0.0))
                results.append(sensor.check(cost))
            elif sensor.name == "citation_presence":
                findings = payload.get("findings", [])
                results.append(sensor.check(findings))
            elif sensor.name == "schema_validation":
                tool_input = payload.get("tool_input", payload)
                results.append(sensor.check(tool_input))
            else:
                results.append(sensor.check(payload))
        return results

    def run_inferential(self, payload: dict[str, Any]) -> list[SensorResult]:
        results: list[SensorResult] = []
        for sensor in self._inferential.values():
            results.append(sensor.check(payload))
        return results

    def run_all(self, payload: dict[str, Any]) -> list[SensorResult]:
        return self.run_computational(payload) + self.run_inferential(payload)

    def to_report(self, results: list[SensorResult]) -> dict[str, Any]:
        passed = [r.sensor_name for r in results if r.passed]
        failed = [r.sensor_name for r in results if not r.passed]
        blocking_failed = [r.sensor_name for r in results if not r.passed and r.blocking]
        return {
            "passed": passed,
            "failed": failed,
            "blocking_failed": blocking_failed,
            "harness_security_score": (
                1.0 if not blocking_failed else max(0.0, 1.0 - len(blocking_failed) / max(len(results), 1))
            ),
        }


def default_registry() -> SensorRegistry:
    """Registry with baseline computational sensors for harness eval hooks."""
    from core.harness.loop import BudgetSensor, CitationSensor, SchemaSensor

    registry = SensorRegistry()
    registry.register(SchemaSensor({}))
    registry.register(BudgetSensor(budget_usd=5.0))
    registry.register(CitationSensor())
    return registry
