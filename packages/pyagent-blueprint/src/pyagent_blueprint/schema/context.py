"""ContextConfigSpec: memory tier configuration + compression + redaction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryConfig(BaseModel):
    """Memory tier configuration."""

    working_max_tokens: int = Field(default=50_000, gt=0)
    session_backend: str = Field(default="json", description="'json' or 'sqlite'")
    semantic_enabled: bool = Field(default=False)


class CompressionConfig(BaseModel):
    """Compression policy configuration."""

    policy: str = Field(default="none", description="none | fifo | semantic_lossless | sawtooth")
    target_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    threshold_tokens: int = Field(default=10_000, gt=0)
    floor_tokens: int = Field(default=5_000, gt=0)


class RedactionConfig(BaseModel):
    """Redaction configuration."""

    max_sensitivity: str = Field(
        default="internal", description="public | internal | confidential | restricted"
    )
    exclude_above: bool = Field(default=False)


class ContextConfigSpec(BaseModel):
    """Context configuration for a blueprint."""

    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    compression: CompressionConfig = Field(default_factory=CompressionConfig)
    redaction: RedactionConfig | None = Field(default=None)
