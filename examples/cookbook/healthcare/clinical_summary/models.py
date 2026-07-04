"""Pydantic models for Clinical Summary."""
from __future__ import annotations
from pydantic import BaseModel


class SummaryRequest(BaseModel):
    patient_id: str
    note: str


class SummaryResponse(BaseModel):
    patient_id: str
    summary: str
    accurate: bool
    safety_flags: list[str]
    cost_usd: float
    trace_file: str


def parse_accurate(output: str) -> bool:
    return output.strip().upper().startswith("ACCURATE")


def parse_safety_flags(output: str) -> list[str]:
    flags: list[str] = []
    in_flags = False
    for line in output.splitlines():
        if "SAFETY FLAGS" in line.upper():
            in_flags = True
            continue
        if in_flags and line.strip().startswith("-"):
            flags.append(line.strip().lstrip("- "))
        elif in_flags and line.strip() and not line.strip().startswith("-"):
            in_flags = False
    return flags
