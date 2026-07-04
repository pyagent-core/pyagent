"""Pydantic models for Startup Simulation."""
from __future__ import annotations
from pydantic import BaseModel


class SimulationRequest(BaseModel):
    sim_id: str
    idea: str


class SimulationResponse(BaseModel):
    sim_id: str
    plan: str
    roles: list[str]
    rounds: int
    cost_usd: float
    trace_file: str
