"""Pydantic I/O models and output parsers for AML Monitoring."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class AlertRequest(BaseModel):
    account_id: str
    transaction: str


class AlertResponse(BaseModel):
    risk_tier: str
    auto_cleared: bool
    sar_filed: bool
    sar_narrative: str
    cost_usd: float
    trace_file: str
    ticket_id: str | None = None


def parse_tier(output: str) -> Literal["Low", "Medium", "High"]:
    """Parse risk tier from agent output without fragile full-string matching."""
    for tier in ("High", "Medium", "Low"):
        if f"— {tier}" in output or f"tier: {tier}" in output.lower():
            return tier
    # Numeric fallback: "score 88" → High
    import re
    m = re.search(r"(?:score|risk)[:\s]+(\d+)", output, re.IGNORECASE)
    if m:
        score = int(m.group(1))
        if score > 70:
            return "High"
        if score >= 30:
            return "Medium"
        return "Low"
    return "Medium"
