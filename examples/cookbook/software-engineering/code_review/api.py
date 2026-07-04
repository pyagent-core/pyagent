"""Code Review System — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import ReviewRequest, ReviewResponse, parse_security_score
from .pipeline import build, run_review

log = logging.getLogger(__name__)
app = FastAPI(title="Code Review API", version="1.0.0")


@app.post("/review", response_model=ReviewResponse)
async def review_code(req: ReviewRequest) -> ReviewResponse:
    trace_file = f"traces/code_review/{req.pr_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("code_review")
    try:
        safe, hitl, security_scan = build(bus, tracker, recorder)
        reviewed = await run_review(safe, req.code)
        security = await security_scan.run(reviewed.output)
        score    = parse_security_score(security.output)
        recorder.end(reviewed.output)
        exporter.flush()
        log.info("pr=%s security_score=%d cost=%.6f", req.pr_id, score, tracker.total_cost)
        return ReviewResponse(
            pr_id=req.pr_id,
            verdict=reviewed.output,
            security_score=score,
            escalated=(score < 8),
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("code review failed pr=%s", req.pr_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
