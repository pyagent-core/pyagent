"""Decorators for automatic tracing of patterns and agents.

@traced_pattern: wraps a Pattern subclass to emit spans on every run().
@traced_agent: wraps an Agent to emit spans on every run().
"""

from __future__ import annotations

import functools
import time
from typing import TYPE_CHECKING

from opentelemetry import trace

from pyagent_trace.attributes import PyAgentAttributes

if TYPE_CHECKING:
    from pyagent_patterns.base import Agent, Context, Message, Pattern, Result

_tracer = trace.get_tracer("pyagent", "0.1.0")


def traced_pattern(cls: type[Pattern]) -> type[Pattern]:
    """Class decorator: auto-emit OTel spans for every pattern.run() call.

    Usage:
        @traced_pattern
        class MyPattern(Pattern):
            ...
    """
    original_run = cls.run

    @functools.wraps(original_run)
    async def traced_run(self: Pattern, task: str, context: Context | None = None) -> Result:
        with _tracer.start_as_current_span(
            f"pyagent.pattern.{self.pattern_type}",
            attributes={PyAgentAttributes.PATTERN_TYPE: self.pattern_type},
        ) as span:
            start = time.perf_counter()
            try:
                result = await original_run(self, task, context)

                duration_ms = (time.perf_counter() - start) * 1000
                span.set_attribute(PyAgentAttributes.EXEC_DURATION_MS, duration_ms)
                span.set_attribute(PyAgentAttributes.EXEC_TOKEN_ESTIMATE, result.token_estimate)
                span.set_attribute(PyAgentAttributes.COST_TOTAL_USD, result.cost_estimate)

                if "rounds" in result.metadata:
                    span.set_attribute(PyAgentAttributes.PATTERN_ROUNDS, result.metadata["rounds"])

                span.set_status(trace.StatusCode.OK)
                return result
            except Exception as e:
                span.set_status(trace.StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

    cls.run = traced_run  # type: ignore[assignment]
    return cls


def traced_agent(agent: Agent) -> Agent:
    """Wrap an Agent instance to emit OTel spans on every run() call.

    Usage:
        agent = traced_agent(Agent("my_agent", llm))
    """
    original_run = agent.run

    @functools.wraps(original_run)
    async def traced_run(messages: list[Message]) -> Message:
        with _tracer.start_as_current_span(
            f"pyagent.agent.{agent.name}",
            attributes={PyAgentAttributes.AGENT_NAME: agent.name},
        ) as span:
            start = time.perf_counter()
            try:
                result = await original_run(messages)
                duration_ms = (time.perf_counter() - start) * 1000
                span.set_attribute(PyAgentAttributes.EXEC_DURATION_MS, duration_ms)
                span.set_status(trace.StatusCode.OK)
                return result
            except Exception as e:
                span.set_status(trace.StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

    agent.run = traced_run  # type: ignore[assignment]
    return agent
