"""Trading Signal Desk — FastAPI production server."""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import SignalRequest, SignalResponse, parse_conviction, parse_direction
from .pipeline import build, run_signal

log = logging.getLogger(__name__)
app = FastAPI(title="Trading Signal Desk API", version="1.0.0")


@app.post("/signal", response_model=SignalResponse)
async def generate_signal(req: SignalRequest) -> SignalResponse:
    trace_file = f"traces/signals/{req.ticker}/{uuid.uuid4().hex[:8]}.jsonl"

    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("trading_signals")
    try:
        desk   = build(bus, tracker, recorder)
        result = await run_signal(desk, req.market_data)

        recorder.end(result.output)
        exporter.flush()
        log.info("ticker=%s direction=%s cost=%.6f",
                 req.ticker, parse_direction(result.output), tracker.total_cost)
        return SignalResponse(
            ticker=req.ticker,
            direction=parse_direction(result.output),
            conviction=parse_conviction(result.output),
            rationale=result.output,
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("Signal generation failed ticker=%s", req.ticker)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
