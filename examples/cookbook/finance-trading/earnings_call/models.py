"""Pydantic models and parsers for Earnings Call Analyzer."""
from __future__ import annotations
from pydantic import BaseModel


class TranscriptRequest(BaseModel):
    ticker: str
    transcript: str


class BriefResponse(BaseModel):
    ticker: str
    analysis: str
    rounds: int
    complete: bool
    cost_usd: float
    trace_file: str


STOP_PHRASE = "ANALYSIS COMPLETE"


def is_complete(output: str) -> bool:
    return STOP_PHRASE in output
