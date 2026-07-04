"""Pydantic models for Robo-Advisor Onboarding."""
from __future__ import annotations
from pydantic import BaseModel


class OnboardingRequest(BaseModel):
    client_id: str
    answers: str


class OnboardingResponse(BaseModel):
    client_id: str
    suitable: bool
    plan: str
    cost_usd: float
    trace_file: str


def is_suitable(output: str) -> bool:
    return "SUITABLE" in output.upper() and "NOT SUITABLE" not in output.upper()
