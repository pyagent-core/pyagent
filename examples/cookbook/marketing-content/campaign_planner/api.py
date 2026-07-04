#!/usr/bin/env python3
"""Marketing Campaign Planner — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_campaign
from .models import CampaignRequest, CampaignResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Campaign Planner API", version="1.0.0")


@app.post("/plan", response_model=CampaignResponse)
async def plan_campaign(req: CampaignRequest) -> CampaignResponse:
    trace_file = f"traces/campaign_planner/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("campaign_planner")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_campaign(safe, req.brief)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return CampaignResponse(
            product=req.product,
            campaign_plan=result.output,
            channels_covered=result.metadata.get("workers_used", []),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Campaign planning failed product=%s", req.product)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
