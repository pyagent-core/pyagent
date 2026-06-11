"""Tests for ProviderRouter: each routing strategy."""

from __future__ import annotations

import pytest
from pyagent_patterns.base import Message
from pyagent_providers.adapters.mock import MockProvider
from pyagent_providers.registry import ProviderRegistry
from pyagent_providers.router import ProviderRouter, RoutingStrategy
from pyagent_router.selector import Capability


@pytest.fixture
def cheap_provider() -> MockProvider:
    return MockProvider(
        name="cheap",
        responses=["cheap response"],
        models=["gpt-4.1-nano"],
        capabilities={Capability.GENERAL},
        max_context=128_000,
    )


@pytest.fixture
def capable_provider() -> MockProvider:
    return MockProvider(
        name="capable",
        responses=["capable response"],
        models=["gpt-4o", "o3-mini"],
        capabilities={Capability.GENERAL, Capability.CODE, Capability.REASONING, Capability.VISION},
        max_context=200_000,
    )


@pytest.fixture
async def registry(
    cheap_provider: MockProvider, capable_provider: MockProvider
) -> ProviderRegistry:
    reg = ProviderRegistry()
    await reg.register(cheap_provider)
    await reg.register(capable_provider)
    return reg


@pytest.mark.asyncio
async def test_capability_first(registry: ProviderRegistry) -> None:
    router = ProviderRouter(registry, strategy=RoutingStrategy.CAPABILITY_FIRST)
    messages = [Message.user("Write a Python function")]
    provider, _ = await router.route(messages)
    # The capable provider has more capabilities
    assert provider.name == "capable"


@pytest.mark.asyncio
async def test_cost_first(registry: ProviderRegistry) -> None:
    router = ProviderRouter(registry, strategy=RoutingStrategy.COST_FIRST)
    messages = [Message.user("What is 2+2?")]
    provider, model = await router.route(messages)
    # gpt-4.1-nano should be cheapest
    assert model == "gpt-4.1-nano"
    assert provider.name == "cheap"


@pytest.mark.asyncio
async def test_latency_first(registry: ProviderRegistry) -> None:
    router = ProviderRouter(registry, strategy=RoutingStrategy.LATENCY_FIRST)
    messages = [Message.user("Quick question")]
    provider, _ = await router.route(messages)
    # Cheap provider has smaller context = proxy for lower latency
    assert provider.name == "cheap"


@pytest.mark.asyncio
async def test_round_robin(registry: ProviderRegistry) -> None:
    router = ProviderRouter(registry, strategy=RoutingStrategy.ROUND_ROBIN)
    messages = [Message.user("Test")]

    names = set()
    for _ in range(4):
        provider, _ = await router.route(messages)
        names.add(provider.name)

    # Both providers should be hit
    assert names == {"cheap", "capable"}


@pytest.mark.asyncio
async def test_route_with_required_capabilities(registry: ProviderRegistry) -> None:
    router = ProviderRouter(registry, strategy=RoutingStrategy.CAPABILITY_FIRST)
    messages = [Message.user("Analyse this image")]

    # Require VISION — only capable provider has it
    provider, _ = await router.route(messages, required={Capability.VISION})
    assert provider.name == "capable"


@pytest.mark.asyncio
async def test_route_no_candidates_raises() -> None:
    reg = ProviderRegistry()
    router = ProviderRouter(reg, strategy=RoutingStrategy.CAPABILITY_FIRST)
    messages = [Message.user("Test")]

    with pytest.raises(RuntimeError, match="No healthy provider"):
        await router.route(messages)
