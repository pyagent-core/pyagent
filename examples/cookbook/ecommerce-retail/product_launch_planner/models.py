"""Pydantic models for Product Launch Planner."""
from __future__ import annotations
from pydantic import BaseModel


class LaunchRequest(BaseModel):
    launch_id: str
    brief: str


class LaunchResponse(BaseModel):
    launch_id: str
    plan: str
    workers_used: list[str]
    cost_usd: float
    trace_file: str
