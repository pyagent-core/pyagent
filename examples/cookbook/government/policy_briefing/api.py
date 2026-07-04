#!/usr/bin/env python3
"""Policy Briefing Pipeline — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_brief
from .models import BriefingRequest, BriefingResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Policy Briefing API", version="1.0.0")


@app.post("/brief", response_model=BriefingResponse)
async def generate_briefing(req: BriefingRequest) -> BriefingResponse:
    trace_file = f"traces/policy_briefing/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("policy_briefing")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_brief(safe, req.policy_topic)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return BriefingResponse(
            policy_topic=req.policy_topic,
            briefing=result.output,
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Policy briefing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
