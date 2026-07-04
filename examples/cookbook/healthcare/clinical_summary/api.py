"""Clinical Summary — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import SummaryRequest, SummaryResponse, parse_accurate, parse_safety_flags
from .pipeline import build, run_summary

log = logging.getLogger(__name__)
app = FastAPI(title="Clinical Summary API", version="1.0.0")


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_note(req: SummaryRequest) -> SummaryResponse:
    trace_file = f"traces/clinical/{req.patient_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("clinical_summary")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_summary(safe, req.note)
        recorder.end(result.output)
        exporter.flush()
        log.info("patient=%s accurate=%s cost=%.6f",
                 req.patient_id, parse_accurate(result.output), tracker.total_cost)
        return SummaryResponse(
            patient_id=req.patient_id,
            summary=result.output,
            accurate=parse_accurate(result.output),
            safety_flags=parse_safety_flags(result.output),
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("summarization failed patient=%s", req.patient_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
