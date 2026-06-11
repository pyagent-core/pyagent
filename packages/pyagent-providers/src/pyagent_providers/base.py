"""Core types: ProviderProtocol, ProviderCapabilities, HealthStatus, ProviderInfo."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pyagent_router.selector import Capability

if TYPE_CHECKING:
    from pyagent_patterns.base import Message


class HealthStatus(StrEnum):
    """Health status of a provider."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class ProviderCapabilities:
    """Declares what a provider can do.

    Attributes:
        models: List of model identifiers this provider exposes.
        capabilities: Set of capability tags (reuses pyagent_router.Capability).
        max_context: Maximum context window in tokens across all models.
        supports_streaming: Whether the provider supports token-level streaming.
        supports_tools: Whether the provider supports tool/function calling.
        supports_vision: Whether the provider supports image inputs.
    """

    models: list[str]
    capabilities: set[Capability] = field(default_factory=lambda: {Capability.GENERAL})
    max_context: int = 128_000
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False


@dataclass(frozen=True)
class ProviderInfo:
    """Snapshot of provider state returned by the registry.

    Attributes:
        name: Provider name.
        capabilities: Provider capabilities.
        health: Current health status.
        metadata: Arbitrary extra metadata (e.g. region, version).
    """

    name: str
    capabilities: ProviderCapabilities
    health: HealthStatus
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ProviderProtocol(Protocol):
    """Interface that every LLM provider must implement.

    Also satisfies ``LLMCallable`` via ``__call__`` which delegates to
    ``complete`` with a default model.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this provider."""
        ...

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Declared capabilities."""
        ...

    async def health(self) -> HealthStatus:
        """Check current health of the provider endpoint."""
        ...

    async def complete(self, messages: list[Message], model: str | None = None) -> str:
        """Generate a completion.

        Args:
            messages: Conversation history.
            model: Optional model override. Uses provider default if ``None``.

        Returns:
            The assistant response text.
        """
        ...

    async def __call__(self, messages: list[Message]) -> str:
        """LLMCallable-compatible entry point — delegates to ``complete``."""
        ...
