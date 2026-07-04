"""Pydantic models for Compliance Checker."""
from __future__ import annotations
from pydantic import BaseModel


class CheckRequest(BaseModel):
    doc_id: str
    regulation: str
    policies: str


class CheckResponse(BaseModel):
    doc_id: str
    gap_report: str
    gap_count: int
    cost_usd: float
    trace_file: str
