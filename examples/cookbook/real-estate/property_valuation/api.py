#!/usr/bin/env python3
"""Property Valuation Stack — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_valuation
from .models import ValuationRequest, ValuationResponse

log = logging.getLogger(__name__)
app = FastAPI(title="Property Valuation API", version="1.0.0")


@app.post("/value", response_model=ValuationResponse)
async def value_property(req: ValuationRequest) -> ValuationResponse:
    trace_file = f"traces/property_valuation/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("property_valuation")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_valuation(safe, req.property_description)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return ValuationResponse(
            property_address=req.property_address,
            valuation_report=result.output,
            estimated_value=result.metadata.get("estimated_value"),
            confidence=result.metadata.get("confidence", "medium"),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("Property valuation failed address=%s", req.property_address)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
