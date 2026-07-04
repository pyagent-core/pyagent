"""Pydantic models for Campaign Planner."""
from __future__ import annotations
from pydantic import BaseModel


class CampaignRequest(BaseModel):
    campaign_id: str
    brief: str


class CampaignResponse(BaseModel):
    campaign_id: str
    campaign: str
    cost_usd: float
    trace_file: str
