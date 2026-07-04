#!/usr/bin/env python3
"""Product Launch Planner — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_plan
from .models import LaunchRequest, LaunchResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Product Launch Planner API", version="1.0.0")


@app.post("/plan", response_model=LaunchResponse)
async def plan_launch(req: LaunchRequest) -> LaunchResponse:
    trace_file = f"traces/product_launch/{req.product_name.replace(' ', '_')}/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("product_launch_planner")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_plan(safe, req.brief)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return LaunchResponse(
            product_name=req.product_name,
            launch_plan=result.output,
            workers_used=result.metadata.get("workers_used", []),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Launch planning failed product=%s", req.product_name)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
