"""Security Log Triage — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import AlertRequest, AlertResponse, parse_disposition
from .pipeline import build, run_triage

log = logging.getLogger(__name__)
app = FastAPI(title="Security Log Triage API", version="1.0.0")


@app.post("/triage", response_model=AlertResponse)
async def triage_alert(req: AlertRequest) -> AlertResponse:
    trace_file = f"traces/soc/{req.alert_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("log_triage")
    try:
        safe, _hitl = build(bus, tracker, recorder)
        result      = await run_triage(safe, req.raw_alert)
        disposition = parse_disposition(result.output)
        recorder.end(result.output)
        exporter.flush()
        log.info("alert=%s disposition=%s cost=%.6f",
                 req.alert_id, disposition, tracker.total_cost)
        return AlertResponse(
            alert_id=req.alert_id,
            case_note=result.output,
            disposition=disposition,
            escalated=(disposition == "ESCALATE"),
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("triage failed alert=%s", req.alert_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
