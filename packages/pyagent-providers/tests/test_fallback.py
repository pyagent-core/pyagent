"""Tests for FallbackChain: primary fails → fallback, all fail, circuit breaker."""

from __future__ import annotations

import pytest

from pyagent_patterns.base import Message
from pyagent_providers.adapters.mock import MockProvider
from pyagent_providers.base import HealthStatus
from pyagent_providers.fallback import FallbackChain


class FailingProvider(MockProvider):
    """A provider that always raises on complete()."""

    async def complete(self, messages: list[Message], model: str | None = None) -> str:
        raise ConnectionError("Provider unavailable")

    async def __call__(self, messages: list[Message]) -> str:
        return await self.complete(messages)


@pytest.fixture
def primary() -> FailingProvider:
    return FailingProvider(name="primary", responses=["should not see this"])


@pytest.fixture
def fallback() -> MockProvider:
    return MockProvider(name="fallback", responses=["fallback response"])


@pytest.fixture
def messages() -> list[Message]:
    return [Message.user("Test task")]


@pytest.mark.asyncio
async def test_primary_succeeds(fallback: MockProvider, messages: list[Message]) -> None:
    healthy = MockProvider(name="primary", responses=["primary response"])
    chain = FallbackChain(providers=[healthy, fallback])
    result = await chain.complete(messages)
    assert result.output == "primary response"
    assert result.provider_name == "primary"
    assert len(result.attempts) == 1
    assert result.attempts[0].success is True


@pytest.mark.asyncio
async def test_primary_fails_fallback_succeeds(
    primary: FailingProvider,
    fallback: MockProvider,
    messages: list[Message],
) -> None:
    chain = FallbackChain(providers=[primary, fallback])
    result = await chain.complete(messages)
    assert result.output == "fallback response"
    assert result.provider_name == "fallback"
    assert len(result.attempts) == 2
    assert result.attempts[0].success is False
    assert "ConnectionError" in (result.attempts[0].error or "")
    assert result.attempts[1].success is True


@pytest.mark.asyncio
async def test_all_fail_raises(primary: FailingProvider, messages: list[Message]) -> None:
    another_failing = FailingProvider(name="also_failing")
    chain = FallbackChain(providers=[primary, another_failing])

    with pytest.raises(RuntimeError, match="All providers failed"):
        await chain.complete(messages)


@pytest.mark.asyncio
async def test_callable_interface(fallback: MockProvider, messages: list[Message]) -> None:
    chain = FallbackChain(providers=[fallback])
    result = await chain(messages)
    assert result == "fallback response"


@pytest.mark.asyncio
async def test_circuit_breaker_skips_open(
    primary: FailingProvider,
    fallback: MockProvider,
    messages: list[Message],
) -> None:
    """When a circuit breaker is open, skip that provider."""

    class FakeCircuitBreaker:
        class state:
            pass

    class OpenCB:
        pass

    # Simulate an open circuit breaker
    from pyagent_patterns.recovery import CircuitState

    class MockCB:
        state = CircuitState.OPEN

    chain = FallbackChain(
        providers=[primary, fallback],
        circuit_breakers={"primary": MockCB()},
    )

    result = await chain.complete(messages)
    assert result.provider_name == "fallback"
    assert result.attempts[0].error == "circuit_open"
    assert result.attempts[0].provider_name == "primary"


def test_empty_providers_raises() -> None:
    with pytest.raises(ValueError, match="at least one provider"):
        FallbackChain(providers=[])
