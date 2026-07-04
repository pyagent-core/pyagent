"""Pydantic models for Loan Underwriting Committee."""
from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel


class UnderwritingRequest(BaseModel):
    application_id: str
    application: str


class UnderwritingResponse(BaseModel):
    application_id: str
    decision: str
    rationale: str
    cost_usd: float
    trace_file: str


def parse_decision(output: str) -> Literal["APPROVE", "APPROVE WITH CONDITIONS", "DECLINE", "REFER"]:
    if "APPROVE WITH CONDITIONS" in output.upper():
        return "APPROVE WITH CONDITIONS"
    if "APPROVE" in output.upper():
        return "APPROVE"
    if "DECLINE" in output.upper():
        return "DECLINE"
    return "REFER"
