"""Pydantic models for Writers Room."""
from __future__ import annotations
from pydantic import BaseModel


class EpisodeRequest(BaseModel):
    show_id: str
    premise: str


class EpisodeResponse(BaseModel):
    show_id: str
    outline: str
    cost_usd: float
    trace_file: str
