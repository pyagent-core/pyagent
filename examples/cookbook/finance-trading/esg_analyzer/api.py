"""ESG Report Analyzer — FastAPI production server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import ESGRequest, ESGResponse, parse_rating
from .pipeline import build, run_esg

log = logging.getLogger(__name__)
app = FastAPI(title="ESG Report Analyzer API", version="1.0.0")


@app.post("/analyze", response_model=ESGResponse)
async def analyze_esg(req: ESGRequest) -> ESGResponse:
    trace_file = f"traces/esg/{req.company.replace(' ', '_')}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("esg_analysis")
    try:
        brief  = f"Company: {req.company}\nMandate: {req.mandate}"
        safe   = build(bus, tracker, recorder)
        result = await run_esg(safe, brief)
        recorder.end(result.output)
        exporter.flush()
        return ESGResponse(
            company=req.company,
            rating=parse_rating(result.output),
            summary=result.output,
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
