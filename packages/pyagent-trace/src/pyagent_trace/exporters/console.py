"""ConsoleExporter — prints trace events to stdout for development/debugging."""

from __future__ import annotations

import sys
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from pyagent_trace.events import TraceEvent


class ConsoleExporter:
    """Export trace events to stdout (or any file-like object).

    Usage:
        exporter = ConsoleExporter()
        bus.subscribe(exporter.export_event)
    """

    def __init__(self, output: IO[str] | None = None) -> None:
        self._output = output or sys.stdout

    def export_event(self, event: TraceEvent) -> None:
        """Print a formatted trace event."""
        parts = [f"[{event.event_type}]"]
        if event.pattern_type:
            parts.append(f"pattern={event.pattern_type}")
        if event.agent_name:
            parts.append(f"agent={event.agent_name}")
        if event.payload:
            payload_str = " ".join(f"{k}={v}" for k, v in event.payload.items())
            parts.append(payload_str)
        line = " ".join(parts)
        self._output.write(line + "\n")

    def flush(self) -> None:
        """Flush the output stream."""
        self._output.flush()

    def shutdown(self) -> None:
        """Flush remaining output."""
        self.flush()
