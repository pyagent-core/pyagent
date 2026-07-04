"""Pydantic models for Property Valuation."""
from __future__ import annotations
from pydantic import BaseModel


class ValuationRequest(BaseModel):
    property_id: str
    listing: str


class ValuationResponse(BaseModel):
    property_id: str
    report: str
    confidence: str
    cost_usd: float
    trace_file: str


def parse_confidence(output: str) -> str:
    """Extract 'high', 'medium', or 'low' confidence level from output."""
    lower = output.lower()
    for level in ("high", "medium", "low"):
        if level in lower:
            return level
    return "low"
