"""Pydantic models and parsers for Wealth Rebalancing Crew."""
from __future__ import annotations
from pydantic import BaseModel


class RebalanceRequest(BaseModel):
    client_id: str
    mandate: str
    current_holdings: str


class RebalanceResponse(BaseModel):
    client_id: str
    compliant: bool
    proposal: str
    cost_usd: float
    trace_file: str


def is_compliant(output: str) -> bool:
    return "COMPLIANT" in output.upper() and "VIOLATION" not in output.upper()
