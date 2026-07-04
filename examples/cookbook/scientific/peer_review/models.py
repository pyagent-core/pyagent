"""Pydantic models for Peer Review."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class ManuscriptRequest(BaseModel):
    ms_id: str
    manuscript: str


class ManuscriptResponse(BaseModel):
    ms_id: str
    consensus: str
    decision: str
    cost_usd: float
    trace_file: str


def parse_decision(output: str) -> Literal["accept", "major_revision", "reject"]:
    """Extract peer review decision from output."""
    lower = output.lower()
    if "major revision" in lower or "major_revision" in lower:
        return "major_revision"
    if "accept" in lower:
        return "accept"
    if "reject" in lower:
        return "reject"
    return "major_revision"
