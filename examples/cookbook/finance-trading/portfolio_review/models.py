"""Pydantic models for Portfolio Review."""
from __future__ import annotations
import re
from pydantic import BaseModel


class ReviewRequest(BaseModel):
    portfolio_id: str
    holding: str


class ReviewResponse(BaseModel):
    portfolio_id: str
    memo: str
    score: int
    cost_usd: float
    trace_file: str


def parse_score(output: str) -> int:
    m = re.search(r"(?:score|rating)[:\s]+(\d+)", output, re.IGNORECASE)
    if m:
        return min(10, max(1, int(m.group(1))))
    return 7
