"""WorkflowSpec: pattern + agent wiring + recovery configuration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RecoverySpec(BaseModel):
    """Bounded execution / recovery configuration."""

    max_retries: int = Field(default=2, ge=0)
    timeout_seconds: float = Field(default=30.0, gt=0)
    fallback_provider: str = Field(default="", description="Provider ref to use on failure")


class WorkflowSpec(BaseModel):
    """Specification of a workflow: pattern + agent wiring."""

    pattern: str = Field(..., description="Pattern registry name (e.g., 'supervisor', 'pipeline')")
    agents: dict[str, Any] = Field(default_factory=dict, description="Role → agent ref mapping")
    config: dict[str, Any] = Field(default_factory=dict, description="Pattern-specific config")
    recovery: RecoverySpec | None = Field(default=None, description="Recovery configuration")
    guardrails: list[str] = Field(default_factory=list, description="Guardrail refs")
