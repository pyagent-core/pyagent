"""Contract Review — FastAPI server."""
from __future__ import annotations
import logging, uuid
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .models import ContractRequest, ContractResponse, parse_approved
from .pipeline import build, run_review

log = logging.getLogger(__name__)
app = FastAPI(title="Contract Review API", version="1.0.0")


@app.post("/review", response_model=ContractResponse)
async def review(req: ContractRequest) -> ContractResponse:
    trace_file = f"traces/contracts/{req.contract_id}/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("contract_review")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_review(safe, req.clause)
        recorder.end(result.output); exporter.flush()
        return ContractResponse(
            contract_id=req.contract_id, redlines=result.output,
            approved=parse_approved(result.output),
            cost_usd=tracker.total_cost, trace_file=trace_file)
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
