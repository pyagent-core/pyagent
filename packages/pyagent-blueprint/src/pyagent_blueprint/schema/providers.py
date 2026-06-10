"""ProviderBindingSpec: model + provider reference for a blueprint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderBindingSpec(BaseModel):
    """Binding of a logical provider name to a model + backend."""

    model: str = Field(..., description="Model identifier (e.g., 'gpt-4.1-mini')")
    provider: str = Field(default="mock", description="Provider backend (mock, openai, anthropic, litellm)")
    fallback_ref: str = Field(default="", description="Fallback provider ref name")
