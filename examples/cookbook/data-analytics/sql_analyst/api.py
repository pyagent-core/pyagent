#!/usr/bin/env python3
"""SQL Analytics Assistant — FastAPI service."""
from __future__ import annotations
import uuid, logging
from fastapi import FastAPI, HTTPException
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.jsonl import JsonlExporter
from .pipeline import build, run_query
from .models import QueryRequest, QueryResponse

log = logging.getLogger(__name__)
app = FastAPI(title="SQL Analyst API", version="1.0.0")


@app.post("/query", response_model=QueryResponse)
async def query_data(req: QueryRequest) -> QueryResponse:
    trace_file = f"traces/sql_analyst/{uuid.uuid4().hex[:8]}.jsonl"
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus); exporter = JsonlExporter(trace_file)
    bus.subscribe(exporter.export_event)
    recorder.start("sql_analyst")
    try:
        safe = build(bus, tracker, recorder)
        result = await run_query(safe, req.question)
        recorder.end(result.output); exporter.flush()
        s = tracker.summary()
        return QueryResponse(
            question=req.question,
            answer=result.output,
            steps_taken=result.metadata.get("steps", 0),
            tools_used=result.metadata.get("tools_used", []),
            cost_usd=s["total_cost_usd"],
            trace_file=trace_file,
        )
    except Exception as exc:
        recorder.end(f"ERROR: {exc}"); exporter.flush()
        log.exception("SQL query failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict: return {"status": "ok"}
