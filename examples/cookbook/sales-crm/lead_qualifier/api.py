#!/usr/bin/env python3
"""Lead Qualifier — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_qualify
from .models import LeadRequest, LeadResponse, parse_tier

log = logging.getLogger(__name__)
app = FastAPI(title="Lead Qualifier API", version="1.0.0")


@app.post("/qualify", response_model=LeadResponse)
async def qualify_lead(req: LeadRequest) -> LeadResponse:
    trace_file = f"traces/lead_qualifier/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("lead_qualifier")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_qualify(safe, req.lead_description)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        tier = result.metadata.get("route") or parse_tier(result.output)
        return LeadResponse(
            company=req.company,
            tier=tier,
            action=result.output,
            worker_used=result.metadata.get("worker_used", ""),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Lead qualification failed company=%s", req.company)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
