"""Wealth Rebalancing Crew — FastAPI production server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import RebalanceRequest, RebalanceResponse, is_compliant
from .pipeline import build, run_rebalance

log = logging.getLogger(__name__)
app = FastAPI(title="Wealth Rebalancing API", version="1.0.0")


@app.post("/rebalance", response_model=RebalanceResponse)
async def rebalance(req: RebalanceRequest) -> RebalanceResponse:
    trace_file = f"traces/rebalance/{req.client_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("rebalance")
    try:
        brief = f"{req.mandate}\n\nCurrent holdings:\n{req.current_holdings}"
        safe_pipeline = build(bus, tracker, recorder)
        result = await run_rebalance(safe_pipeline, brief)
        recorder.end(result.output)
        exporter.flush()
        return RebalanceResponse(
            client_id=req.client_id,
            compliant=is_compliant(result.output),
            proposal=result.output,
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
