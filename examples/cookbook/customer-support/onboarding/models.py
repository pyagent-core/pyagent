"""Pydantic models for Customer Onboarding."""
from __future__ import annotations
from pydantic import BaseModel


class OnboardingRequest(BaseModel):
    customer_id: str
    customer_info: str


class OnboardingResponse(BaseModel):
    customer_id: str
    summary: str
    roles_completed: list[str]
    cost_usd: float
    trace_file: str
