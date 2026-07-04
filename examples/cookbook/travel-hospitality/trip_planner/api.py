#!/usr/bin/env python3
"""Trip-Planning Swarm — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_trip
from .models import TripRequest, TripResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Trip Planner API", version="1.0.0")


@app.post("/plan", response_model=TripResponse)
async def plan_trip(req: TripRequest) -> TripResponse:
    trace_file = f"traces/trip_planner/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("trip_planner")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_trip(safe, req.trip_request)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return TripResponse(
            destination=req.destination,
            itinerary=result.output,
            agents_used=result.metadata.get("agents_used", []),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Trip planning failed destination=%s", req.destination)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
