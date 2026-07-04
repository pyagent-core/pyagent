#!/usr/bin/env python3
"""Essay Grader — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_grade
from .models import GradeRequest, GradeResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Essay Grader API", version="1.0.0")


@app.post("/grade", response_model=GradeResponse)
async def grade_essay(req: GradeRequest) -> GradeResponse:
    trace_file = f"traces/essay_grader/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("essay_grader")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_grade(safe, req.essay_text)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        grade_data = result.metadata
        return GradeResponse(
            grade=parse_grade(result.output),
            feedback=result.output,
            tally=grade_data.get("tally", {}),
            consensus=grade_data.get("consensus", False),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Essay grading failed")
        raise HTTPException(status_code=500, detail=str(exc))


def parse_grade(output: str) -> str:
    for g in ("A", "B", "C", "D", "F"):
        if f"Grade: {g}" in output or f"grade: {g}" in output.lower():
            return g
    return "B"


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
