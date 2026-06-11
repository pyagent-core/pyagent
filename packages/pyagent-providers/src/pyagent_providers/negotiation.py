"""CapabilityNegotiator: match task requirements to the best provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyagent_router.selector import Capability

    from pyagent_providers.base import ProviderProtocol
    from pyagent_providers.registry import ProviderRegistry


@dataclass(frozen=True)
class NegotiationResult:
    """Result of capability negotiation.

    Attributes:
        provider: The best-matched provider.
        model: Recommended model from that provider.
        match_score: How well the provider matches (0.0-1.0).
        matched_capabilities: Which requested capabilities the provider satisfies.
        missing_capabilities: Which requested capabilities the provider lacks.
    """

    provider: ProviderProtocol
    model: str
    match_score: float
    matched_capabilities: set[Capability] = field(default_factory=set)
    missing_capabilities: set[Capability] = field(default_factory=set)


class CapabilityNegotiator:
    """Find the best provider for a given set of task requirements.

    Scores providers by capability overlap, context window adequacy,
    and feature support (streaming, tools, vision).

    Args:
        registry: Provider registry to search.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def negotiate(
        self,
        required_capabilities: set[Capability] | None = None,
        *,
        min_context: int = 0,
        needs_streaming: bool = False,
        needs_tools: bool = False,
        needs_vision: bool = False,
    ) -> NegotiationResult | None:
        """Find the best provider matching the requirements.

        Args:
            required_capabilities: Must-have capabilities.
            min_context: Minimum context window size in tokens.
            needs_streaming: Whether streaming is required.
            needs_tools: Whether tool/function calling is required.
            needs_vision: Whether image input is required.

        Returns:
            Best ``NegotiationResult``, or ``None`` if no provider qualifies.
        """
        required = required_capabilities or set()
        candidates = self._registry.discover(healthy_only=True)

        if not candidates:
            return None

        scored: list[tuple[ProviderProtocol, float, set[Capability], set[Capability]]] = []

        for provider in candidates:
            caps = provider.capabilities

            # Hard filters
            if min_context > 0 and caps.max_context < min_context:
                continue
            if needs_streaming and not caps.supports_streaming:
                continue
            if needs_tools and not caps.supports_tools:
                continue
            if needs_vision and not caps.supports_vision:
                continue

            # Score: capability match ratio
            if required:
                matched = required & caps.capabilities
                missing = required - caps.capabilities
                cap_score = len(matched) / len(required) if required else 1.0
            else:
                matched = caps.capabilities
                missing = set()
                cap_score = 1.0

            # Bonus for extra capabilities
            bonus = min(len(caps.capabilities - required) * 0.05, 0.2) if required else 0.0

            # Bonus for large context
            context_bonus = min(caps.max_context / 1_000_000, 0.1)

            total_score = min(cap_score + bonus + context_bonus, 1.0)
            scored.append((provider, total_score, matched, missing))

        if not scored:
            return None

        scored.sort(key=lambda x: x[1], reverse=True)
        best_provider, best_score, best_matched, best_missing = scored[0]

        # Pick the most capable model from the provider
        models = best_provider.capabilities.models
        model = models[-1] if models else ""

        return NegotiationResult(
            provider=best_provider,
            model=model,
            match_score=best_score,
            matched_capabilities=best_matched,
            missing_capabilities=best_missing,
        )

    def negotiate_all(
        self,
        required_capabilities: set[Capability] | None = None,
        *,
        min_context: int = 0,
        needs_streaming: bool = False,
        needs_tools: bool = False,
        needs_vision: bool = False,
        limit: int = 5,
    ) -> list[NegotiationResult]:
        """Return all matching providers ranked by score.

        Same args as ``negotiate`` plus ``limit`` to cap results.
        """
        required = required_capabilities or set()
        candidates = self._registry.discover(healthy_only=True)
        results: list[NegotiationResult] = []

        for provider in candidates:
            caps = provider.capabilities

            if min_context > 0 and caps.max_context < min_context:
                continue
            if needs_streaming and not caps.supports_streaming:
                continue
            if needs_tools and not caps.supports_tools:
                continue
            if needs_vision and not caps.supports_vision:
                continue

            if required:
                matched = required & caps.capabilities
                missing = required - caps.capabilities
                cap_score = len(matched) / len(required)
            else:
                matched = caps.capabilities
                missing = set()
                cap_score = 1.0

            bonus = min(len(caps.capabilities - required) * 0.05, 0.2) if required else 0.0
            context_bonus = min(caps.max_context / 1_000_000, 0.1)
            total_score = min(cap_score + bonus + context_bonus, 1.0)

            models = provider.capabilities.models
            model = models[-1] if models else ""

            results.append(
                NegotiationResult(
                    provider=provider,
                    model=model,
                    match_score=total_score,
                    matched_capabilities=matched,
                    missing_capabilities=missing,
                )
            )

        results.sort(key=lambda r: r.match_score, reverse=True)
        return results[:limit]
