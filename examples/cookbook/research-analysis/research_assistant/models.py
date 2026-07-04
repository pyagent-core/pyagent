"""Pydantic models for Research Assistant."""
from __future__ import annotations
from pydantic import BaseModel


class ResearchRequest(BaseModel):
    query_id: str
    question: str


class ResearchResponse(BaseModel):
    query_id: str
    report: str
    cost_usd: float
    trace_file: str
