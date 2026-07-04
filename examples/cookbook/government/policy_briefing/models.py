"""Pydantic models for Policy Briefing."""
from __future__ import annotations
from pydantic import BaseModel


class BriefingRequest(BaseModel):
    brief_id: str
    question: str


class BriefingResponse(BaseModel):
    brief_id: str
    brief: str
    cost_usd: float
    trace_file: str
