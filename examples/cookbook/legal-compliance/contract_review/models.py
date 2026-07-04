"""Pydantic models for Contract Review."""
from __future__ import annotations
from pydantic import BaseModel


class ContractRequest(BaseModel):
    contract_id: str
    clause: str


class ContractResponse(BaseModel):
    contract_id: str
    redlines: str
    approved: bool
    cost_usd: float
    trace_file: str


def parse_approved(output: str) -> bool:
    return "APPROVED" in output.upper()
