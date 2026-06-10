"""AgentSpec: agent definition within a blueprint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    """Specification of a single agent."""

    prompt: str = Field(..., description="System prompt for this agent")
    provider: str = Field(default="", description="Provider ref from providers dict")
    tools: list[str] = Field(default_factory=list, description="Tool names available to this agent")
    description: str = Field(default="", description="What this agent does")
    guardrails: list[str] = Field(default_factory=list, description="Guardrail refs")
