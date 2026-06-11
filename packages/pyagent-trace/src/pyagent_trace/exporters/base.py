"""TraceExporter protocol — the portal-agnostic contract for exporting trace events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pyagent_trace.events import TraceEvent


@runtime_checkable
class TraceExporter(Protocol):
    """Portal-agnostic exporter contract.

    Any class implementing these three methods can receive pyagent trace events.
    Built-in: ConsoleExporter, JsonlExporter, OTelExporter, LangfuseExporter.
    Users can implement custom exporters for any backend.
    """

    def export_event(self, event: TraceEvent) -> None:
        """Export a single trace event to the backend."""
        ...

    def flush(self) -> None:
        """Flush any buffered events to the backend."""
        ...

    def shutdown(self) -> None:
        """Shutdown the exporter, flushing remaining events."""
        ...
