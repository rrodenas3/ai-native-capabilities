"""Tests for harness sensor registry."""

from __future__ import annotations

import pytest

from core.harness.loop import BudgetSensor, ComputationalSensor, SensorResult, SensorType
from core.harness.sensors import SensorRegistry, UnknownSensorError, default_registry


class EchoSensor(ComputationalSensor):
    name = "echo_sensor"
    blocking = False

    def check(self, payload: dict) -> SensorResult:
        return SensorResult(
            sensor_name=self.name,
            sensor_type=SensorType.COMPUTATIONAL,
            passed=bool(payload.get("ok")),
            message=str(payload.get("msg", "")),
        )


def test_register_and_run_computational() -> None:
    registry = SensorRegistry()
    registry.register(EchoSensor())
    results = registry.run_computational({"ok": True, "msg": "fine"})
    assert len(results) == 1
    assert results[0].passed


def test_unknown_sensor_raises() -> None:
    registry = SensorRegistry()
    with pytest.raises(UnknownSensorError):
        registry.get("missing")


def test_default_registry_has_baseline_sensors() -> None:
    registry = default_registry()
    results = registry.run_computational({"findings": [{"finding_id": "F1", "citations": ["c1"]}]})
    assert results
    report = registry.to_report(results)
    assert "harness_security_score" in report


def test_to_report_flags_blocking_failures() -> None:
    class FailSensor(ComputationalSensor):
        name = "fail_sensor"
        blocking = True

        def check(self, payload: dict) -> SensorResult:
            return SensorResult(
                sensor_name=self.name,
                sensor_type=SensorType.COMPUTATIONAL,
                passed=False,
                blocking=True,
            )

    registry = SensorRegistry()
    registry.register(FailSensor())
    report = registry.to_report(registry.run_computational({}))
    assert report["blocking_failed"] == ["fail_sensor"]
    assert report["harness_security_score"] < 1.0
