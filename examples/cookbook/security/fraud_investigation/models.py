"""Pydantic models for Fraud Investigation."""
from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel


class InvestigationRequest(BaseModel):
    alert_id: str
    alert: str


class InvestigationResponse(BaseModel):
    alert_id: str
    case_file: str
    risk_level: str
    steps_taken: int
    tools_used: list[str]
    cost_usd: float
    trace_file: str


def parse_risk_level(output: str) -> Literal["Low", "Medium", "High"]:
    for level in ("High", "Medium", "Low"):
        if level.lower() in output.lower():
            return level  # type: ignore[return-value]
    return "Medium"
