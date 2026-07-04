"""Pydantic models for Analytics Decomposer."""
from __future__ import annotations
from pydantic import BaseModel


class AnalyticsRequest(BaseModel):
    request_id: str
    question: str


class AnalyticsResponse(BaseModel):
    request_id: str
    analysis: str
    workers_used: list[str]
    cost_usd: float
    trace_file: str
