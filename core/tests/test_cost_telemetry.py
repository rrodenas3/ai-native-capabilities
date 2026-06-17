from __future__ import annotations

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from core.observability import (
    MODEL_PRICING,
    CostTelemetry,
    configure_tracer_provider,
    trace_agent_hop,
)
from core.schemas.base import AgentHop, AgentHopType


def test_model_pricing_contains_current_models() -> None:
    assert MODEL_PRICING["claude-sonnet-4-6"] == {"input": 3.00, "output": 15.00}
    assert "gpt-4o" not in MODEL_PRICING


def test_record_llm_call_logs_required_fields_and_cost() -> None:
    telemetry = CostTelemetry()

    event = telemetry.record_llm_call(
        model="claude-sonnet-4-6",
        tokens_in=1_000_000,
        tokens_out=1_000_000,
        latency_ms=123.0,
        agent_name="supervisor",
        run_id="run-1",
    )

    assert event.model == "claude-sonnet-4-6"
    assert event.tokens_in == 1_000_000
    assert event.tokens_out == 1_000_000
    assert event.latency_ms == 123.0
    assert event.agent_name == "supervisor"
    assert event.run_id == "run-1"
    assert event.cost_usd == 18.0


def test_get_run_cost_sums_only_matching_run() -> None:
    telemetry = CostTelemetry()
    telemetry.record_llm_call("gpt-5-mini", 1_000_000, 0, 1.0, "router", "run-1")
    telemetry.record_llm_call("gpt-5-mini", 0, 1_000_000, 1.0, "router", "run-1")
    telemetry.record_llm_call("gpt-5-mini", 1_000_000, 1_000_000, 1.0, "router", "run-2")

    assert telemetry.get_run_cost("run-1") == 2.0


def test_unknown_model_raises_value_error() -> None:
    telemetry = CostTelemetry()

    with pytest.raises(ValueError):
        telemetry.record_llm_call("gpt-4o", 1, 1, 1.0, "agent", "run")


def test_budget_alert_fires_at_80_percent_threshold() -> None:
    alerts = []
    telemetry = CostTelemetry(budget_alert_handler=lambda *args: alerts.append(args), session_budget_usd=1.0)

    telemetry.record_llm_call("gpt-5-mini", 1_000_000, 500_000, 1.0, "router", "run-1")

    assert alerts == [("run-1", 1.2, 0.8)]


def test_otel_span_created_for_agent_hop() -> None:
    exporter = InMemorySpanExporter()
    configure_tracer_provider(exporter)
    hop = AgentHop(
        agent_name="supervisor",
        hop_type=AgentHopType.SUPERVISOR,
        model="claude-sonnet-4-6",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=50.0,
    )

    with trace_agent_hop(hop):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs["agent.name"] == "supervisor"
    assert attrs["llm.model"] == "claude-sonnet-4-6"
    assert attrs["llm.tokens_in"] == 10
    assert attrs["llm.tokens_out"] == 20
    assert attrs["llm.cost_usd"] == 0.001
