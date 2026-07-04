"""Startup Simulation — FastAPI server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import ROUNDS
from .models import SimulationRequest, SimulationResponse
from .pipeline import build, run_simulation

log = logging.getLogger(__name__)
app = FastAPI(title="Startup Simulation API", version="1.0.0")


@app.post("/simulate", response_model=SimulationResponse)
async def simulate(req: SimulationRequest) -> SimulationResponse:
    trace_file = f"traces/startup/{req.sim_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("startup_simulation")
    try:
        safe   = build(bus, tracker, recorder)
        result = await run_simulation(safe, req.idea)
        recorder.end(result.output)
        exporter.flush()
        log.info("sim=%s roles=%s cost=%.6f",
                 req.sim_id, result.metadata.get("roles", []), tracker.total_cost)
        return SimulationResponse(
            sim_id=req.sim_id,
            plan=result.output,
            roles=result.metadata.get("roles", []),
            rounds=result.metadata.get("rounds", ROUNDS),
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("simulation failed sim=%s", req.sim_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
