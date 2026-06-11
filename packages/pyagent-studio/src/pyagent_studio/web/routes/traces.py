"""Traces page — live SSE trace events + historical JSONL viewer."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from fastapi import APIRouter, Request
from pyagent_trace.events import TraceEvent, TraceEventBus
from starlette.responses import StreamingResponse

router = APIRouter()

# Global event bus for live trace streaming
_trace_bus = TraceEventBus()


def get_trace_bus() -> TraceEventBus:
    """Get the global trace event bus (for wiring producers)."""
    return _trace_bus


@router.get("/")
async def traces_page(request: Request):
    """Render traces page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "traces.html", context={})


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
                    data = json.dumps(asdict(event), default=str)
                    yield f"data: {data}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _trace_bus.unsubscribe(sub_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
