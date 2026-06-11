"""MockProvider: wraps MockLLM with ProviderProtocol for testing."""

from __future__ import annotations

from pyagent_patterns.base import Message, MockLLM
from pyagent_router.selector import Capability

from pyagent_providers.base import HealthStatus, ProviderCapabilities


class MockProvider:
    """A mock provider for testing that wraps ``MockLLM``.

    Implements the full ``ProviderProtocol`` interface with configurable
    capabilities and health status.

    Args:
        name: Unique provider name.
        responses: Canned responses passed to ``MockLLM``.
        models: List of model names this mock exposes.
        capabilities: Capability set.
        max_context: Max context window.
        health_status: Fixed health status to return.
        delay: Simulated latency in seconds.
    """

    def __init__(
        self,
        name: str = "mock",
        responses: list[str] | None = None,
        models: list[str] | None = None,
        capabilities: set[Capability] | None = None,
        max_context: int = 128_000,
        health_status: HealthStatus = HealthStatus.HEALTHY,
        delay: float = 0.0,
    ) -> None:
        self._name = name
        self._llm = MockLLM(responses=responses, delay=delay)
        self._capabilities = ProviderCapabilities(
            models=models or ["mock-model"],
            capabilities=capabilities or {Capability.GENERAL},
            max_context=max_context,
        )
        self._health_status = health_status

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def health(self) -> HealthStatus:
        return self._health_status

    async def complete(self, messages: list[Message], model: str | None = None) -> str:
        return await self._llm(messages)

    async def __call__(self, messages: list[Message]) -> str:
        return await self.complete(messages)

    def set_health(self, status: HealthStatus) -> None:
        """Change health status (for test scenarios)."""
        self._health_status = status

    @property
    def call_count(self) -> int:
        return self._llm.call_count

    @property
    def call_log(self) -> list[list[Message]]:
        return self._llm.call_log
