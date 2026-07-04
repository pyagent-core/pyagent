"""Pydantic models for Security Log Triage."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class AlertRequest(BaseModel):
    alert_id: str
    raw_alert: str


class AlertResponse(BaseModel):
    alert_id: str
    case_note: str
    disposition: str
    escalated: bool
    cost_usd: float
    trace_file: str


def parse_disposition(output: str) -> Literal["FALSE_POSITIVE", "ESCALATE"]:
    if "FALSE_POSITIVE" in output.upper():
        return "FALSE_POSITIVE"
    return "ESCALATE"


def _create_soc_case(summary: str, metadata: dict) -> str:
    import httpx, os
    r = httpx.post(
        os.environ.get("SOC_TICKETING_URL", "http://localhost:8080") + "/cases",
        json={"summary": summary[:300], "source": "log-triage-agent", **metadata},
        headers={"Authorization": f"Bearer {os.environ.get('SOC_TICKETING_TOKEN', '')}"},
        timeout=15.0,
    )
    r.raise_for_status()
    return str(r.json()["case_id"])
