"""Pydantic models for Trip Planner."""
from __future__ import annotations
from pydantic import BaseModel


class TripRequest(BaseModel):
    trip_id: str
    brief: str


class TripResponse(BaseModel):
    trip_id: str
    itinerary: str
    cost_usd: float
    trace_file: str
