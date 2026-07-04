"""Pydantic models for ESG Report Analyzer."""
from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel


class ESGRequest(BaseModel):
    company: str
    mandate: str


class ESGResponse(BaseModel):
    company: str
    rating: str
    summary: str
    cost_usd: float
    trace_file: str


def parse_rating(output: str) -> str:
    m = re.search(r"ESG rating[:\s]+([A-E][+-]?)", output, re.IGNORECASE)
    if m:
        return m.group(1)
    for grade in ("A", "B", "C", "D", "E"):
        if f"rating: {grade}" in output or f"Rating {grade}" in output:
            return grade
    return "C"
