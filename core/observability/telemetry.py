"""OpenTelemetry helpers for agent hops."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter

from core.schemas.base import AgentHop


def configure_tracer_provider(
    exporter: SpanExporter | None = None,
    *,
    force: bool = False,
) -> TracerProvider:
    current_provider = trace.get_tracer_provider()
    if not force and not isinstance(current_provider, trace.ProxyTracerProvider):
        if not isinstance(current_provider, TracerProvider):
            raise RuntimeError("An external tracer provider is already configured")
        return current_provider

    provider = TracerProvider()
    if exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


@contextmanager
def trace_agent_hop(hop: AgentHop) -> Iterator[None]:
    tracer = trace.get_tracer("ai-native-capabilities")
    with tracer.start_as_current_span(f"agent.{hop.agent_name}") as span:
        span.set_attribute("agent.name", hop.agent_name)
        span.set_attribute("agent.hop_type", hop.hop_type.value)
        span.set_attribute("llm.model", hop.model)
        span.set_attribute("llm.tokens_in", hop.tokens_in)
        span.set_attribute("llm.tokens_out", hop.tokens_out)
        span.set_attribute("llm.cost_usd", hop.cost_usd)
        span.set_attribute("agent.latency_ms", hop.latency_ms)
        span.set_attribute("agent.success", hop.success)
        if hop.confidence is not None:
            span.set_attribute("agent.confidence", hop.confidence)
        if hop.error is not None:
            span.set_attribute("agent.error", hop.error)
        yield
