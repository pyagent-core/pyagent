"""Pydantic I/O models and output parsers for Trading Signal Desk."""
from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel


class SignalRequest(BaseModel):
    ticker: str
    market_data: str


class SignalResponse(BaseModel):
    ticker: str
    direction: str
    conviction: int
    rationale: str
    cost_usd: float
    trace_file: str


def parse_direction(output: str) -> Literal["LONG", "SHORT", "FLAT"]:
    for d in ("LONG", "SHORT", "FLAT"):
        if d in output.upper():
            return d
    return "FLAT"


def parse_conviction(output: str) -> int:
    m = re.search(r"conviction[:\s]+(\d+)", output, re.IGNORECASE)
    if m:
        return min(10, max(1, int(m.group(1))))
    return 5
