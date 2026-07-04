"""CV Screener — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import ScreenRequest, ScreenResponse, parse_rubric_scores, parse_verdict
from .pipeline import build, run_screen

log = logging.getLogger(__name__)
app = FastAPI(title="CV Screener API", version="1.0.0")


@app.post("/screen", response_model=ScreenResponse)
async def screen_cv(req: ScreenRequest) -> ScreenResponse:
    trace_file = f"traces/cv/{req.job_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("cv_screener")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_screen(safe, req.cv)
        scores  = parse_rubric_scores(result.output)
        overall = round(sum(scores.values()) / max(len(scores), 1))
        recorder.end(result.output)
        exporter.flush()
        log.info("job=%s verdict=%s cost=%.6f", req.job_id, parse_verdict(result.output), tracker.total_cost)
        return ScreenResponse(
            job_id=req.job_id,
            verdict=parse_verdict(result.output),
            scores=scores,
            overall=overall,
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("screening failed job=%s", req.job_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
