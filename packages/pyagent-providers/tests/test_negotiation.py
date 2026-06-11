"""Tests for CapabilityNegotiator: match capabilities, filtering, ranking."""

from __future__ import annotations

import pytest
from pyagent_providers.adapters.mock import MockProvider
from pyagent_providers.negotiation import CapabilityNegotiator
from pyagent_providers.registry import ProviderRegistry
from pyagent_router.selector import Capability


@pytest.fixture
async def registry() -> ProviderRegistry:
    reg = ProviderRegistry()
    await reg.register(
        MockProvider(
            name="basic",
            models=["basic-model"],
            capabilities={Capability.GENERAL},
            max_context=32_000,
        )
    )
    await reg.register(
        MockProvider(
            name="pro",
            models=["pro-small", "pro-large"],
            capabilities={
                Capability.GENERAL,
                Capability.CODE,
                Capability.REASONING,
                Capability.VISION,
            },
            max_context=200_000,
        )
    )
    await reg.register(
        MockProvider(
            name="creative",
            models=["creative-model"],
            capabilities={Capability.GENERAL, Capability.CREATIVE},
            max_context=128_000,
        )
    )
    return reg


@pytest.mark.asyncio
async def test_negotiate_best_match(registry: ProviderRegistry) -> None:
    negotiator = CapabilityNegotiator(registry)
    result = negotiator.negotiate(required_capabilities={Capability.CODE, Capability.REASONING})
    assert result is not None
    assert result.provider.name == "pro"
    assert result.match_score > 0.5
    assert Capability.CODE in result.matched_capabilities
    assert Capability.REASONING in result.matched_capabilities
    assert len(result.missing_capabilities) == 0


@pytest.mark.asyncio
async def test_negotiate_partial_match(registry: ProviderRegistry) -> None:
    negotiator = CapabilityNegotiator(registry)
    result = negotiator.negotiate(required_capabilities={Capability.CODE, Capability.CREATIVE})
    # Neither provider has both — pro has CODE but not CREATIVE
    assert result is not None
    # Pro should rank highest because it has CODE + more extras
    assert result.provider.name == "pro"
    assert Capability.CODE in result.matched_capabilities
    assert Capability.CREATIVE in result.missing_capabilities


@pytest.mark.asyncio
async def test_negotiate_with_min_context(registry: ProviderRegistry) -> None:
    negotiator = CapabilityNegotiator(registry)
    result = negotiator.negotiate(min_context=100_000)
    # basic has only 32k — should be excluded
    assert result is not None
    assert result.provider.name in {"pro", "creative"}


@pytest.mark.asyncio
async def test_negotiate_with_vision(registry: ProviderRegistry) -> None:
    negotiator = CapabilityNegotiator(registry)
    # MockProvider defaults supports_vision=False
    result = negotiator.negotiate(needs_vision=True)
    # All mocks have supports_vision=False by default, so no match
    assert result is None


@pytest.mark.asyncio
async def test_negotiate_no_requirements(registry: ProviderRegistry) -> None:
    negotiator = CapabilityNegotiator(registry)
    result = negotiator.negotiate()
    assert result is not None
    # All providers match (no filter), highest context bonus wins
    assert result.provider.name in {"basic", "pro", "creative"}


@pytest.mark.asyncio
async def test_negotiate_all(registry: ProviderRegistry) -> None:
    negotiator = CapabilityNegotiator(registry)
    results = negotiator.negotiate_all(required_capabilities={Capability.GENERAL})
    assert len(results) == 3  # all three have GENERAL
    # Ranked by score descending
    assert results[0].match_score >= results[1].match_score
    assert results[1].match_score >= results[2].match_score


@pytest.mark.asyncio
async def test_negotiate_empty_registry() -> None:
    reg = ProviderRegistry()
    negotiator = CapabilityNegotiator(reg)
    result = negotiator.negotiate({Capability.CODE})
    assert result is None
