"""Portfolio Review — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import ReviewRequest, ReviewResponse, parse_score
from .pipeline import build, run_review

log = logging.getLogger(__name__)
app = FastAPI(title="Portfolio Review API", version="1.0.0")


@app.post("/review", response_model=ReviewResponse)
async def review_holding(req: ReviewRequest) -> ReviewResponse:
    trace_file = f"traces/portfolio/{req.portfolio_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("portfolio_review")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_review(safe, req.holding)
        score  = parse_score(result.output)
        recorder.end(result.output)
        exporter.flush()
        log.info("portfolio=%s score=%d cost=%.6f", req.portfolio_id, score, tracker.total_cost)
        return ReviewResponse(
            portfolio_id=req.portfolio_id,
            memo=result.output,
            score=score,
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("portfolio review failed portfolio=%s", req.portfolio_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
