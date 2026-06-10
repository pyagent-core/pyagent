"""ContractSpec: input/output schema + SLA constraints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SLASpec(BaseModel):
    """Service-level agreement for a workflow."""

    latency_p95_ms: float = Field(default=5000.0, gt=0)
    cost_max_usd: float = Field(default=0.10, gt=0)
    quality_min: float = Field(default=0.0, ge=0.0, le=1.0)


class ContractSpec(BaseModel):
    """Input/output contract for a workflow."""

    input: dict[str, Any] = Field(default_factory=dict, description="Input schema (JSON Schema-like)")
    output: dict[str, Any] = Field(default_factory=dict, description="Output schema (JSON Schema-like)")
    sla: SLASpec = Field(default_factory=SLASpec, description="SLA constraints")
