#!/usr/bin/env python3
"""Writers' Room — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_room, ROUNDS
from .models import PitchRequest, PitchResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Writers' Room API", version="1.0.0")


@app.post("/develop", response_model=PitchResponse)
async def develop_pitch(req: PitchRequest) -> PitchResponse:
    trace_file = f"traces/writers_room/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("writers_room")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_room(safe, req.episode_pitch)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return PitchResponse(
            episode_pitch=req.episode_pitch,
            developed_script=result.output,
            rounds=ROUNDS,
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Writers' room failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
