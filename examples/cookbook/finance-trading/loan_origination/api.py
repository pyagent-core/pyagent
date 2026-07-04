"""Loan Origination Workflow — FastAPI production server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import OriginationRequest, OriginationResponse, is_complete, parse_decision
from .pipeline import build, run_origination

log = logging.getLogger(__name__)
app = FastAPI(title="Loan Origination API", version="1.0.0")


@app.post("/originate", response_model=OriginationResponse)
async def originate(req: OriginationRequest) -> OriginationResponse:
    trace_file = f"traces/origination/{req.application_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("loan_origination")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_origination(safe, req.application)
        recorder.end(result.output)
        exporter.flush()
        return OriginationResponse(
            application_id=req.application_id,
            decision=parse_decision(result.output),
            complete=is_complete(result.output),
            output=result.output,
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
