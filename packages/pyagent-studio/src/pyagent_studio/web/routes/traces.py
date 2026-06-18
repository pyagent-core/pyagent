"""Traces page — live SSE trace events + historical JSONL viewer."""

from __future__ import annotations

import asyncio
import html
from datetime import datetime

from fastapi import APIRouter, Request
from pyagent_trace.events import TraceEvent, TraceEventBus
from starlette.responses import StreamingResponse

router = APIRouter()


def _render_row(event: TraceEvent) -> str:
    """Render a TraceEvent as an HTML table row for the live SSE stream."""
    ts = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S") if event.timestamp else "—"
    who = event.agent_name or event.pattern_type or "—"
    detail = (
        event.payload.get("task")
        or event.payload.get("model")
        or event.payload.get("result_output", "")
    )
    cells = [ts, event.event_type, who, str(detail)[:80]]
    tds = "".join(f"<td>{html.escape(c)}</td>" for c in cells)
    return f"<tr>{tds}</tr>"


# Global event bus for live trace streaming
_trace_bus = TraceEventBus()


def get_trace_bus() -> TraceEventBus:
    """Get the global trace event bus (for wiring producers)."""
    return _trace_bus


@router.get("/")
async def traces_page(request: Request):
    """Render traces page."""
    from pyagent_studio.web.routes._common import base_context

    templates = request.app.state.templates
    return templates.TemplateResponse(request, "traces.html", context=base_context(request))


@router.get("/live")
async def traces_live_sse(request: Request):
    """SSE endpoint for live trace events."""

    async def event_generator():
        queue: asyncio.Queue[TraceEvent] = asyncio.Queue()
        sub_id = _trace_bus.subscribe(lambda e: queue.put_nowait(e))
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {_render_row(event)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _trace_bus.unsubscribe(sub_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
