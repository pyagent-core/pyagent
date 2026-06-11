"""PyAgent Trace — pattern-aware OpenTelemetry tracing for multi-agent LLM systems."""

from pyagent_trace.attributes import PyAgentAttributes
from pyagent_trace.cost import CostTracker
from pyagent_trace.events import TraceEvent, TraceEventBus
from pyagent_trace.exporters.base import TraceExporter
from pyagent_trace.recorder import Recorder


# OTel-dependent imports are lazy to avoid hard dependency
def __getattr__(name: str):
    if name == "traced_agent":
        from pyagent_trace.decorators import traced_agent

        return traced_agent
    if name == "traced_pattern":
        from pyagent_trace.decorators import traced_pattern

        return traced_pattern
    if name == "PatternSpanEmitter":
        from pyagent_trace.spans import PatternSpanEmitter

        return PatternSpanEmitter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CostTracker",
    "PatternSpanEmitter",
    "PyAgentAttributes",
    "Recorder",
    "TraceEvent",
    "TraceEventBus",
    "TraceExporter",
    "traced_agent",
    "traced_pattern",
]
__version__ = "0.1.0"
