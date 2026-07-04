"""Loan Underwriting Committee — FastAPI production server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import UnderwritingRequest, UnderwritingResponse, parse_decision
from .pipeline import build, run_committee

log = logging.getLogger(__name__)
app = FastAPI(title="Loan Underwriting Committee API", version="1.0.0")


@app.post("/underwrite", response_model=UnderwritingResponse)
async def underwrite(req: UnderwritingRequest) -> UnderwritingResponse:
    trace_file = f"traces/underwriting/{req.application_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("loan_underwriting")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_committee(safe, req.application)
        recorder.end(result.output)
        exporter.flush()
        decision = parse_decision(result.output)
        return UnderwritingResponse(
            application_id=req.application_id,
            decision=decision,
            rationale=result.output,
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
