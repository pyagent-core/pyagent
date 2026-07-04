"""Pydantic models for CV Screener."""
from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel


class ScreenRequest(BaseModel):
    job_id: str
    cv: str


class ScreenResponse(BaseModel):
    job_id: str
    verdict: str
    scores: dict[str, int]
    overall: int
    cost_usd: float
    trace_file: str


def parse_verdict(output: str) -> Literal["STRONG HIRE", "HIRE", "NO HIRE"]:
    out = output.upper()
    if "STRONG HIRE" in out:
        return "STRONG HIRE"
    if "NO HIRE" in out:
        return "NO HIRE"
    if "HIRE" in out:
        return "HIRE"
    return "NO HIRE"


def parse_rubric_scores(output: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for rubric in ("skills", "experience", "collaboration"):
        m = re.search(rf"{rubric}[:\s]+(\d+)", output, re.IGNORECASE)
        if m:
            scores[rubric] = min(10, max(0, int(m.group(1))))
    return scores
