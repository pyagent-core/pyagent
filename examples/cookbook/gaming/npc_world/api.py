#!/usr/bin/env python3
"""Emergent NPC World — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_world
from .models import WorldRequest, WorldResponse

log = logging.getLogger(__name__)
app = FastAPI(title="NPC World Simulation API", version="1.0.0")


@app.post("/simulate", response_model=WorldResponse)
async def simulate_world(req: WorldRequest) -> WorldResponse:
    trace_file = f"traces/npc_world/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("npc_world")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_world(safe, req.initial_state)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return WorldResponse(
            world_state=result.output,
            blackboard=result.metadata.get("blackboard", {}),
            rounds_completed=result.metadata.get("rounds", 0),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("NPC world simulation failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
