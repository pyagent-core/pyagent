"""Customer Support Router — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import SupportRequest, SupportResponse, parse_intent
from .pipeline import build, run_support

log = logging.getLogger(__name__)
app = FastAPI(title="Customer Support Router API", version="1.0.0")


@app.post("/support", response_model=SupportResponse)
async def route_support(req: SupportRequest) -> SupportResponse:
    trace_file = f"traces/support/{req.ticket_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("support_router")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_support(safe, req.query)
        intent = parse_intent(result.output)
        recorder.end(result.output)
        exporter.flush()
        log.info("ticket=%s intent=%s cost=%.6f", req.ticket_id, intent, tracker.total_cost)
        return SupportResponse(
            ticket_id=req.ticket_id,
            intent=intent,
            reply=result.output,
            escalated=(intent == "escalate"),
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("support routing failed ticket=%s", req.ticket_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
