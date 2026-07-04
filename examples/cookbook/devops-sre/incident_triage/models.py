"""Pydantic models for Incident Triage Pipeline."""
from __future__ import annotations
from pydantic import BaseModel


class TriageRequest(BaseModel):
    incident_id: str
    alert: str


class TriageResponse(BaseModel):
    incident_id: str
    runbook: str
    touches_prod: bool
    approved: bool
    cost_usd: float
    trace_file: str


def parse_touches_prod(output: str) -> bool:
    first_line = output.strip().splitlines()[0].lower() if output.strip() else ""
    return "yes" in first_line


def parse_approved(output: str) -> bool:
    return "rejected" not in output.lower() and "REJECTED" not in output
