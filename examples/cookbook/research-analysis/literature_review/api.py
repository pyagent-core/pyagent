#!/usr/bin/env python3
"""Literature Review Team — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_review
from .models import ReviewRequest, ReviewResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Literature Review API", version="1.0.0")


@app.post("/review", response_model=ReviewResponse)
async def review_literature(req: ReviewRequest) -> ReviewResponse:
    trace_file = f"traces/literature_review/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("literature_review")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_review(safe, req.research_question)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return ReviewResponse(
            research_question=req.research_question,
            literature_review=result.output,
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Literature review failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
