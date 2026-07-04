"""Fraud Investigation — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import InvestigationRequest, InvestigationResponse, parse_risk_level
from .pipeline import build, run_investigation

log = logging.getLogger(__name__)
app = FastAPI(title="Fraud Investigation API", version="1.0.0")


@app.post("/investigate", response_model=InvestigationResponse)
async def investigate_alert(req: InvestigationRequest) -> InvestigationResponse:
    trace_file = f"traces/fraud/{req.alert_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("fraud_investigation")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_investigation(safe, req.alert)
        recorder.end(result.output)
        exporter.flush()
        risk = parse_risk_level(result.output)
        log.info("alert=%s risk=%s cost=%.6f", req.alert_id, risk, tracker.total_cost)
        return InvestigationResponse(
            alert_id=req.alert_id,
            case_file=result.output,
            risk_level=risk,
            steps_taken=result.metadata.get("steps", 0),
            tools_used=result.metadata.get("tools_used", []),
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("investigation failed alert=%s", req.alert_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
