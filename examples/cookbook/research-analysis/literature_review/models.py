"""Pydantic models for Literature Review."""
from __future__ import annotations
from pydantic import BaseModel


class ReviewRequest(BaseModel):
    review_id: str
    question: str


class ReviewResponse(BaseModel):
    review_id: str
    review: str
    cost_usd: float
    trace_file: str
