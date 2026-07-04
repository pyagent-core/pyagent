"""Incident Triage Pipeline — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import TriageRequest, TriageResponse, parse_touches_prod, parse_approved
from .pipeline import build, run_triage

log = logging.getLogger(__name__)
app = FastAPI(title="Incident Triage API", version="1.0.0")


@app.post("/triage", response_model=TriageResponse)
async def triage_incident(req: TriageRequest) -> TriageResponse:
    trace_file = f"traces/incidents/{req.incident_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("incident_triage")
    try:
        safe, _hitl = build(bus, tracker, recorder)
        result      = await run_triage(safe, req.alert)
        recorder.end(result.output)
        exporter.flush()
        log.info("incident=%s touches_prod=%s cost=%.6f",
                 req.incident_id, parse_touches_prod(result.output), tracker.total_cost)
        return TriageResponse(
            incident_id=req.incident_id,
            runbook=result.output,
            touches_prod=parse_touches_prod(result.output),
            approved=parse_approved(result.output),
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("triage failed incident=%s", req.incident_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
