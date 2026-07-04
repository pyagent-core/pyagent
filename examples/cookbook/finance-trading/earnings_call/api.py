"""Earnings Call Analyzer — FastAPI production server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import BriefResponse, TranscriptRequest, is_complete
from .pipeline import build, run_analysis

log = logging.getLogger(__name__)
app = FastAPI(title="Earnings Call Analyzer API", version="1.0.0")


@app.post("/analyze", response_model=BriefResponse)
async def analyze_transcript(req: TranscriptRequest) -> BriefResponse:
    trace_file = f"traces/earnings/{req.ticker}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("earnings_call")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_analysis(safe, req.transcript)
        recorder.end(result.output)
        exporter.flush()
        return BriefResponse(
            ticker=req.ticker,
            analysis=result.output,
            rounds=result.metadata.get("rounds", 1),
            complete=is_complete(result.output),
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
