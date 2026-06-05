"""PatternSpanEmitter: create OTel spans for pattern executions.

Emits structured spans with pyagent.* attributes for every pattern run,
agent call, and routing/compression decision.
"""

from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode

from pyagent_trace.attributes import PyAgentAttributes

_tracer = trace.get_tracer("pyagent", "0.1.0")


class PatternSpanEmitter:
    """Emit OTel spans for pattern executions.

    Usage:
        emitter = PatternSpanEmitter()
        with emitter.pattern_span("debate", {"rounds": 3}) as span:
            # ... pattern logic ...
            emitter.set_result(span, result)
    """

    def pattern_span(
        self,
        pattern_type: str,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Start a span for a pattern execution."""
        span = _tracer.start_span(
            f"pyagent.pattern.{pattern_type}",
            attributes={
                PyAgentAttributes.PATTERN_TYPE: pattern_type,
                **(attributes or {}),
            },
        )
        return span

    def agent_span(
        self,
        agent_name: str,
        parent_span: Span | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Start a span for an individual agent call."""
        ctx = trace.set_span_in_context(parent_span) if parent_span else None
        span = _tracer.start_span(
            f"pyagent.agent.{agent_name}",
            context=ctx,
            attributes={
                PyAgentAttributes.AGENT_NAME: agent_name,
                **(attributes or {}),
            },
        )
        return span

    @staticmethod
    def set_pattern_result(
        span: Span,
        output_length: int,
        rounds: int | None = None,
        consensus: float | None = None,
        escalated: bool = False,
        duration_ms: float = 0.0,
        token_estimate: int = 0,
        cost_estimate: float = 0.0,
    ) -> None:
        """Set result attributes on a pattern span."""
        if rounds is not None:
            span.set_attribute(PyAgentAttributes.PATTERN_ROUNDS, rounds)
        if consensus is not None:
            span.set_attribute(PyAgentAttributes.PATTERN_CONSENSUS, consensus)
        span.set_attribute(PyAgentAttributes.PATTERN_ESCALATED, escalated)
        span.set_attribute(PyAgentAttributes.EXEC_DURATION_MS, duration_ms)
        span.set_attribute(PyAgentAttributes.EXEC_TOKEN_ESTIMATE, token_estimate)
        span.set_attribute(PyAgentAttributes.COST_TOTAL_USD, cost_estimate)
        span.set_status(StatusCode.OK)

    @staticmethod
    def set_routing_info(
        span: Span,
        difficulty: int,
        selected_model: str,
        cost_estimate: float,
        category: str = "",
    ) -> None:
        """Set routing attributes on a span."""
        span.set_attribute(PyAgentAttributes.ROUTER_DIFFICULTY, difficulty)
        span.set_attribute(PyAgentAttributes.ROUTER_SELECTED_MODEL, selected_model)
        span.set_attribute(PyAgentAttributes.ROUTER_COST_ESTIMATE, cost_estimate)
        if category:
            span.set_attribute(PyAgentAttributes.ROUTER_DIFFICULTY_CATEGORY, category)

    @staticmethod
    def set_compression_info(
        span: Span,
        input_tokens: int,
        output_tokens: int,
        savings_pct: float,
    ) -> None:
        """Set compression attributes on a span."""
        span.set_attribute(PyAgentAttributes.COMPRESS_INPUT_TOKENS, input_tokens)
        span.set_attribute(PyAgentAttributes.COMPRESS_OUTPUT_TOKENS, output_tokens)
        span.set_attribute(PyAgentAttributes.COMPRESS_SAVINGS_PCT, savings_pct)

    @staticmethod
    def set_error(span: Span, error: Exception) -> None:
        """Record an error on a span."""
        span.set_status(StatusCode.ERROR, str(error))
        span.record_exception(error)
