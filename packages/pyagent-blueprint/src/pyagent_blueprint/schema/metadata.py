"""MetadataSpec: name, version, description, tags, owner."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MetadataSpec(BaseModel):
    """Blueprint metadata."""

    name: str = Field(..., description="Human-readable blueprint name")
    version: str = Field(default="0.1.0", description="Semantic version")
    description: str = Field(default="", description="What this blueprint does")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    owner: str = Field(default="", description="Team or individual owner")
