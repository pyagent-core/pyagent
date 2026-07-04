"""Pydantic models for NPC World."""
from __future__ import annotations
from pydantic import BaseModel


class WorldRequest(BaseModel):
    world_id: str
    scenario: str


class WorldResponse(BaseModel):
    world_id: str
    chronicle: str
    rounds: int
    cost_usd: float
    trace_file: str
