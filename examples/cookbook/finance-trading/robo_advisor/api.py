"""Robo-Advisor Onboarding — FastAPI production server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import OnboardingRequest, OnboardingResponse, is_suitable
from .pipeline import build, run_onboarding

log = logging.getLogger(__name__)
app = FastAPI(title="Robo-Advisor Onboarding API", version="1.0.0")


@app.post("/onboard", response_model=OnboardingResponse)
async def onboard(req: OnboardingRequest) -> OnboardingResponse:
    trace_file = f"traces/robo/{req.client_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("robo_advisor")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_onboarding(safe, req.answers)
        recorder.end(result.output)
        exporter.flush()
        return OnboardingResponse(
            client_id=req.client_id,
            suitable=is_suitable(result.output),
            plan=result.output,
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
