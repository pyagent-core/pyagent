#!/usr/bin/env python3
"""Peer-Review Mesh — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_review
from .models import PaperRequest, ReviewResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Peer Review API", version="1.0.0")


@app.post("/review", response_model=ReviewResponse)
async def review_paper(req: PaperRequest) -> ReviewResponse:
    trace_file = f"traces/peer_review/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("peer_review")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_review(safe, req.paper_text)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return ReviewResponse(
            paper_title=req.paper_title,
            review=result.output,
            recommendation=result.metadata.get("recommendation", "major_revision"),
            reviewer_count=result.metadata.get("reviewer_count", 4),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Peer review failed paper=%s", req.paper_title)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
