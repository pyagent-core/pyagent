"""WorkflowSpec: pattern + agent wiring + recovery configuration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecoverySpec(BaseModel):
    """Bounded execution / recovery configuration."""

    max_retries: int = Field(default=2, ge=0)
    timeout_seconds: float = Field(default=30.0, gt=0)
    fallback_provider: str = Field(default="", description="Provider ref to use on failure")


class WorkflowSpec(BaseModel):
    """Specification of a workflow: pattern + agent wiring."""

    # Agent/pattern wiring (routes, stages, teams, ...) must be nested under
    # `agents:`/`config:` — a misplaced sibling key (e.g. `classifier:` next
    # to `pattern:` instead of inside `agents:`) is silently dropped under
    # the default "ignore extra" behavior, producing an empty `agents={}`
    # that only fails at run time with a confusing AttributeError deep in
    # the pattern's `_execute`. Forbidding extras turns that into a clear,
    # immediate ValidationError at load time.
    model_config = ConfigDict(extra="forbid")

    pattern: str = Field(..., description="Pattern registry name (e.g., 'supervisor', 'pipeline')")
    agents: dict[str, Any] = Field(default_factory=dict, description="Role → agent ref mapping")
    config: dict[str, Any] = Field(default_factory=dict, description="Pattern-specific config")
    recovery: RecoverySpec | None = Field(default=None, description="Recovery configuration")
    guardrails: list[str] = Field(default_factory=list, description="Guardrail refs")
