"""AML Monitoring — FastAPI production server.

Run:
    uvicorn examples.cookbook.finance-trading.aml_monitoring.api:app --reload
"""
from __future__ import annotations
import logging
import uuid

from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter

from .models import AlertRequest, AlertResponse, parse_tier
from .pipeline import _post_case, run_triage, build

log = logging.getLogger(__name__)

app = FastAPI(title="AML Monitoring API", version="1.0.0")


@app.post("/monitor", response_model=AlertResponse)
async def monitor_transaction(req: AlertRequest) -> AlertResponse:
    trace_file = f"traces/aml/{req.account_id}/{uuid.uuid4().hex[:8]}.jsonl"

    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)

    recorder.start("aml_pipeline")
    try:
        safe_triage, sar_writer = build(bus, tracker, recorder, account_id=req.account_id)
        triage = await run_triage(safe_triage, req.transaction)
        tier   = parse_tier(triage.output)

        sar_filed, narrative, ticket_id = False, "", None
        if tier == "High":
            ticket_id  = await _post_case(triage.output, req.account_id)
            sar_result = await sar_writer.run(triage.output)
            sar_filed  = sar_result.metadata.get("approved", False)
            narrative  = sar_result.output

        recorder.end(triage.output)
        exporter.flush()
        log.info("account=%s tier=%s sar=%s cost=%.6f",
                 req.account_id, tier, sar_filed, tracker.total_cost)
        return AlertResponse(
            risk_tier=tier,
            auto_cleared=(tier != "High"),
            sar_filed=sar_filed,
            sar_narrative=narrative,
            cost_usd=tracker.total_cost,
            trace_file=trace_file,
            ticket_id=ticket_id,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}")
        exporter.flush()
        log.exception("AML monitor failed account=%s", req.account_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
