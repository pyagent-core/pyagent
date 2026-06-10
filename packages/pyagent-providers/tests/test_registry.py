"""Tests for ProviderRegistry: register, discover, health check, remove unhealthy."""

from __future__ import annotations

import pytest

from pyagent_providers.base import HealthStatus
from pyagent_providers.registry import ProviderRegistry
from pyagent_providers.adapters.mock import MockProvider
from pyagent_router.selector import Capability


@pytest.fixture
def registry() -> ProviderRegistry:
    return ProviderRegistry()


@pytest.fixture
def openai_mock() -> MockProvider:
    return MockProvider(
        name="openai",
        responses=["Hello from OpenAI"],
        models=["gpt-4o-mini", "gpt-4o"],
        capabilities={Capability.GENERAL, Capability.CODE, Capability.VISION},
    )


@pytest.fixture
def anthropic_mock() -> MockProvider:
    return MockProvider(
        name="anthropic",
        responses=["Hello from Anthropic"],
        models=["claude-haiku-3.5", "claude-sonnet-4"],
        capabilities={Capability.GENERAL, Capability.CODE, Capability.CREATIVE},
    )


@pytest.mark.asyncio
async def test_register_and_get(registry: ProviderRegistry, openai_mock: MockProvider) -> None:
    await registry.register(openai_mock)
    assert registry.count == 1
    assert "openai" in registry
    assert registry.get("openai") is openai_mock


@pytest.mark.asyncio
async def test_register_sync(registry: ProviderRegistry, openai_mock: MockProvider) -> None:
    registry.register_sync(openai_mock)
    assert registry.count == 1
    assert registry.get("openai") is openai_mock


@pytest.mark.asyncio
async def test_list_providers(
    registry: ProviderRegistry,
    openai_mock: MockProvider,
    anthropic_mock: MockProvider,
) -> None:
    await registry.register(openai_mock)
    await registry.register(anthropic_mock)
    infos = registry.list_providers()
    assert len(infos) == 2
    names = {info.name for info in infos}
    assert names == {"openai", "anthropic"}


@pytest.mark.asyncio
async def test_discover_by_capability(
    registry: ProviderRegistry,
    openai_mock: MockProvider,
    anthropic_mock: MockProvider,
) -> None:
    await registry.register(openai_mock)
    await registry.register(anthropic_mock)

    # Both have GENERAL + CODE
    results = registry.discover({Capability.GENERAL, Capability.CODE})
    assert len(results) == 2

    # Only openai has VISION
    results = registry.discover({Capability.VISION})
    assert len(results) == 1
    assert results[0].name == "openai"

    # Only anthropic has CREATIVE
    results = registry.discover({Capability.CREATIVE})
    assert len(results) == 1
    assert results[0].name == "anthropic"


@pytest.mark.asyncio
async def test_discover_excludes_unhealthy(
    registry: ProviderRegistry,
    openai_mock: MockProvider,
    anthropic_mock: MockProvider,
) -> None:
    openai_mock.set_health(HealthStatus.UNHEALTHY)
    await registry.register(openai_mock)
    await registry.register(anthropic_mock)
    await registry.check_health()

    results = registry.discover(healthy_only=True)
    assert len(results) == 1
    assert results[0].name == "anthropic"


@pytest.mark.asyncio
async def test_check_health(registry: ProviderRegistry, openai_mock: MockProvider) -> None:
    await registry.register(openai_mock)
    statuses = await registry.check_health()
    assert statuses["openai"] == HealthStatus.HEALTHY

    openai_mock.set_health(HealthStatus.DEGRADED)
    statuses = await registry.check_health("openai")
    assert statuses["openai"] == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_remove_unhealthy(
    registry: ProviderRegistry,
    openai_mock: MockProvider,
    anthropic_mock: MockProvider,
) -> None:
    openai_mock.set_health(HealthStatus.UNHEALTHY)
    await registry.register(openai_mock)
    await registry.register(anthropic_mock)

    removed = await registry.remove_unhealthy()
    assert "openai" in removed
    assert registry.count == 1
    assert registry.get("openai") is None


@pytest.mark.asyncio
async def test_remove(registry: ProviderRegistry, openai_mock: MockProvider) -> None:
    await registry.register(openai_mock)
    assert registry.count == 1
    registry.remove("openai")
    assert registry.count == 0
    assert "openai" not in registry
