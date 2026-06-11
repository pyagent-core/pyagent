"""OTelExporter — sends trace events as OpenTelemetry spans.

Supports any OTLP-compatible backend: Jaeger, Grafana Tempo, Honeycomb, Datadog, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from opentelemetry import trace

    _HAS_OTEL = True
except ImportError:
    _HAS_OTEL = False
    trace = None  # type: ignore[assignment]

from pyagent_trace.attributes import PyAgentAttributes

if TYPE_CHECKING:
    from pyagent_trace.events import TraceEvent

_SPAN_NAME_MAP: dict[str, str] = {
    "pattern_start": "pyagent.pattern",
    "pattern_end": "pyagent.pattern",
    "agent_start": "pyagent.agent",
    "agent_end": "pyagent.agent",
    "llm_call": "pyagent.llm_call",
    "llm_response": "pyagent.llm_response",
    "routing_decision": "pyagent.routing",
    "compression": "pyagent.compression",
    "error": "pyagent.error",
    "cost_record": "pyagent.cost",
}


class OTelExporter:
    """Export trace events as OpenTelemetry spans.

    Usage:
        exporter = OTelExporter()
        bus.subscribe(exporter.export_event)

    Configure your TracerProvider and SpanProcessor separately via the OTel SDK.
    """

    def __init__(self, tracer_name: str = "pyagent", tracer_version: str = "0.1.0") -> None:
        if not _HAS_OTEL:
            raise ImportError(
                "opentelemetry package not installed. Install with: "
                "pip install opentelemetry-api opentelemetry-sdk"
            )
        self._tracer = trace.get_tracer(tracer_name, tracer_version)

    def export_event(self, event: TraceEvent) -> None:
        """Create an OTel span from a trace event."""
        span_name = _SPAN_NAME_MAP.get(event.event_type, f"pyagent.{event.event_type}")
        attributes: dict[str, Any] = {}

        if event.pattern_type:
            attributes[PyAgentAttributes.PATTERN_TYPE] = event.pattern_type
        if event.agent_name:
            attributes[PyAgentAttributes.AGENT_NAME] = event.agent_name

        # Map payload keys to OTel attributes where applicable
        payload = event.payload
        if "cost_usd" in payload:
            attributes[PyAgentAttributes.COST_TOTAL_USD] = payload["cost_usd"]
        if "model" in payload:
            attributes[PyAgentAttributes.COST_MODEL] = payload["model"]
        if "input_tokens" in payload:
            attributes[PyAgentAttributes.COST_INPUT_TOKENS] = payload["input_tokens"]
        if "output_tokens" in payload:
            attributes[PyAgentAttributes.COST_OUTPUT_TOKENS] = payload["output_tokens"]
        if "duration_ms" in payload:
            attributes[PyAgentAttributes.EXEC_DURATION_MS] = payload["duration_ms"]

        span = self._tracer.start_span(span_name, attributes=attributes)
        if event.event_type == "error":
            span.set_status(trace.StatusCode.ERROR, payload.get("message", ""))
        else:
            span.set_status(trace.StatusCode.OK)
        span.end()

    def flush(self) -> None:
        """No-op — OTel SDK manages its own flush via SpanProcessor."""

    def shutdown(self) -> None:
        """No-op — OTel SDK manages shutdown via TracerProvider."""
