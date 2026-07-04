"""Pydantic models for Lead Qualifier."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class LeadRequest(BaseModel):
    lead_id: str
    lead: str


class LeadResponse(BaseModel):
    lead_id: str
    tier: str
    action: str
    cost_usd: float
    trace_file: str


def parse_tier(output: str) -> Literal["hot", "warm", "cold"]:
    """Extract tier label from the first word of scorer output."""
    first_word = output.strip().lower().split()[0] if output.strip() else "cold"
    if first_word in ("hot", "warm", "cold"):
        return first_word  # type: ignore[return-value]
    return "cold"
