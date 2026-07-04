"""Pydantic models for Loan Origination Workflow."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class OriginationRequest(BaseModel):
    application_id: str
    application: str


class OriginationResponse(BaseModel):
    application_id: str
    decision: str
    complete: bool
    output: str
    cost_usd: float
    trace_file: str


def parse_decision(output: str) -> Literal["APPROVE", "REFER", "DECLINE"]:
    upper = output.upper()
    if "APPROVE" in upper and "DECLINE" not in upper:
        return "APPROVE"
    if "DECLINE" in upper:
        return "DECLINE"
    return "REFER"


def is_complete(output: str) -> bool:
    return "INCOMPLETE" not in output.upper()
