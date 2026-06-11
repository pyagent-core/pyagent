"""LangfuseExporter — sends trace events to Langfuse cloud or self-hosted.

Maps pyagent events to Langfuse's native concepts:
- pattern_start → langfuse.trace()
- agent_start/end → trace.span()
- llm_call → trace.generation()
- cost_record → generation metadata
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyagent_trace.events import TraceEvent

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None  # type: ignore[assignment, misc]


class LangfuseExporter:
    """Export trace events to Langfuse.

    Usage:
        exporter = LangfuseExporter(
            public_key="pk-...",
            secret_key="sk-...",
            host="https://cloud.langfuse.com",
        )
        bus.subscribe(exporter.export_event)

    Requires: pip install pyagent-trace[langfuse]
    """

    def __init__(
        self,
        public_key: str = "",
        secret_key: str = "",
        host: str = "https://cloud.langfuse.com",
        client: Any | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        elif Langfuse is not None:
            self._client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
        else:
            raise ImportError(
                "langfuse package not installed. Install with: pip install pyagent-trace[langfuse]"
            )
        self._active_traces: dict[str, Any] = {}
        self._active_spans: dict[str, Any] = {}

    def export_event(self, event: TraceEvent) -> None:
        """Export a trace event to Langfuse."""
        handler = _EVENT_HANDLERS.get(event.event_type)
        if handler:
            handler(self, event)

    def _handle_pattern_start(self, event: TraceEvent) -> None:
        trace_obj = self._client.trace(
            name=event.pattern_type or "unknown_pattern",
            metadata=event.payload,
        )
        trace_id = event.payload.get("trace_id", event.pattern_type)
        self._active_traces[trace_id] = trace_obj

    def _handle_pattern_end(self, event: TraceEvent) -> None:
        trace_id = event.payload.get("trace_id", event.pattern_type)
        trace_obj = self._active_traces.pop(trace_id, None)
        if trace_obj:
            trace_obj.update(metadata={**event.payload, "completed": True})

    def _handle_agent_start(self, event: TraceEvent) -> None:
        trace_id = event.payload.get("trace_id", event.pattern_type)
        trace_obj = self._active_traces.get(trace_id)
        if trace_obj:
            span = trace_obj.span(
                name=event.agent_name,
                metadata=event.payload,
            )
            self._active_spans[event.agent_name] = span

    def _handle_agent_end(self, event: TraceEvent) -> None:
        span = self._active_spans.pop(event.agent_name, None)
        if span:
            span.end(metadata=event.payload)

    def _handle_llm_call(self, event: TraceEvent) -> None:
        trace_id = event.payload.get("trace_id", event.pattern_type)
        trace_obj = self._active_traces.get(trace_id)
        parent = trace_obj
        if event.agent_name in self._active_spans:
            parent = self._active_spans[event.agent_name]
        if parent:
            parent.generation(
                name=f"llm_call.{event.agent_name}" if event.agent_name else "llm_call",
                model=event.payload.get("model", ""),
                input=event.payload.get("messages_in", ""),
                output=event.payload.get("response", ""),
                usage={
                    "input": event.payload.get("input_tokens", 0),
                    "output": event.payload.get("output_tokens", 0),
                },
                metadata=event.payload,
            )

    def _handle_cost_record(self, event: TraceEvent) -> None:
        trace_id = event.payload.get("trace_id", event.pattern_type)
        trace_obj = self._active_traces.get(trace_id)
        if trace_obj:
            trace_obj.update(
                metadata={
                    "cost_usd": event.payload.get("cost_usd", 0.0),
                    "model": event.payload.get("model", ""),
                    "input_tokens": event.payload.get("input_tokens", 0),
                    "output_tokens": event.payload.get("output_tokens", 0),
                }
            )

    def flush(self) -> None:
        """Flush pending events to Langfuse."""
        self._client.flush()

    def shutdown(self) -> None:
        """Flush and shutdown the Langfuse client."""
        self._client.flush()


_EVENT_HANDLERS: dict[str, Any] = {
    "pattern_start": LangfuseExporter._handle_pattern_start,
    "pattern_end": LangfuseExporter._handle_pattern_end,
    "agent_start": LangfuseExporter._handle_agent_start,
    "agent_end": LangfuseExporter._handle_agent_end,
    "llm_call": LangfuseExporter._handle_llm_call,
    "cost_record": LangfuseExporter._handle_cost_record,
}
