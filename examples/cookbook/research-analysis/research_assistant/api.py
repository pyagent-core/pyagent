"""Research Assistant — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import ResearchRequest, ResearchResponse
from .pipeline import build, run_research

log = logging.getLogger(__name__)
app = FastAPI(title="Research Assistant API", version="1.0.0")


@app.post("/research", response_model=ResearchResponse)
async def run_research_request(req: ResearchRequest) -> ResearchResponse:
    trace_file = f"traces/research/{req.query_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("research_assistant")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_research(safe, req.question)
        recorder.end(result.output)
        exporter.flush()
        log.info("query=%s cost=%.6f", req.query_id, tracker.total_cost)
        return ResearchResponse(
            query_id=req.query_id,
            report=result.output,
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("research failed query=%s", req.query_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
