"""Analytics Decomposer — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import AnalyticsRequest, AnalyticsResponse
from .pipeline import build, run_analytics

log = logging.getLogger(__name__)
app = FastAPI(title="Analytics Decomposer API", version="1.0.0")


@app.post("/analyze", response_model=AnalyticsResponse)
async def analyze(req: AnalyticsRequest) -> AnalyticsResponse:
    trace_file = f"traces/analytics/{req.request_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("analytics_decomposer")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_analytics(safe, req.question)
        recorder.end(result.output)
        exporter.flush()
        log.info("request=%s workers=%s cost=%.6f",
                 req.request_id, result.metadata.get("workers_used", []), tracker.total_cost)
        return AnalyticsResponse(
            request_id=req.request_id,
            analysis=result.output,
            workers_used=result.metadata.get("workers_used", []),
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("analytics failed request=%s", req.request_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
