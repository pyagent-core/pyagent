"""Pydantic schemas for the tool authorization API and recipe."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthorizationRequest(BaseModel):
    """Request payload to test or invoke tool authorization."""

    principal: str = Field(..., description="Subject identity or agent name requesting invocation")
    capability: str = Field(..., description="Target tool name or capability")
    purpose: str = Field(..., description="Declared invocation purpose")
    account_id: str | None = Field(default=None, description="Optional account scope boundary")
    query: str = Field(default="", description="Argument passed to the tool if authorized")


class AuthorizationResponse(BaseModel):
    """Result of an authorization check or tool execution."""

    allowed: bool
    reason_code: str
    record_fingerprint: str | None = None
    obligations: list[str] = Field(default_factory=list)
    output: str | None = None
    latency_ms: float = 0.0
