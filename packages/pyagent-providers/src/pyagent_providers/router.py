"""ProviderRouter: strategy-based routing across multiple providers."""

from __future__ import annotations

import itertools
from enum import StrEnum
from typing import TYPE_CHECKING

from pyagent_router.estimator import CostEstimator
from pyagent_router.scorer import DifficultyScorer

if TYPE_CHECKING:
    from pyagent_patterns.base import Message
    from pyagent_router.selector import Capability

    from pyagent_providers.base import ProviderProtocol
    from pyagent_providers.registry import ProviderRegistry


class RoutingStrategy(StrEnum):
    """How the router picks a provider + model pair."""

    CAPABILITY_FIRST = "capability_first"
    COST_FIRST = "cost_first"
    LATENCY_FIRST = "latency_first"
    ROUND_ROBIN = "round_robin"


class ProviderRouter:
    """Route requests to the best provider + model pair.

    Args:
        registry: The provider registry to draw from.
        strategy: Routing strategy to use.
        cost_estimator: Optional cost estimator for ``COST_FIRST`` strategy.
        scorer: Optional difficulty scorer for capability-based strategies.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_FIRST,
        cost_estimator: CostEstimator | None = None,
        scorer: DifficultyScorer | None = None,
    ) -> None:
        self._registry = registry
        self._strategy = strategy
        self._estimator = cost_estimator or CostEstimator()
        self._scorer = scorer or DifficultyScorer()
        self._rr_cycle: itertools.cycle[str] | None = None

    async def route(
        self,
        messages: list[Message],
        required: set[Capability] | None = None,
    ) -> tuple[ProviderProtocol, str]:
        """Select the best provider and model for a request.

        Args:
            messages: Conversation messages (last user message used for scoring).
            required: Optional capability requirements.

        Returns:
            Tuple of (provider, model_name).

        Raises:
            RuntimeError: If no suitable provider is found.
        """
        candidates = self._registry.discover(required, healthy_only=True)
        if not candidates:
            raise RuntimeError(f"No healthy provider found matching capabilities={required}")

        if self._strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin(candidates)
        if self._strategy == RoutingStrategy.COST_FIRST:
            return self._route_cost_first(candidates, messages)
        if self._strategy == RoutingStrategy.LATENCY_FIRST:
            return self._route_latency_first(candidates)
        # Default: CAPABILITY_FIRST
        return self._route_capability_first(candidates, messages)

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _route_capability_first(
        self,
        candidates: list[ProviderProtocol],
        messages: list[Message],
    ) -> tuple[ProviderProtocol, str]:
        """Pick the provider with the broadest capability set, then its best model."""
        task_text = self._extract_task(messages)
        difficulty = self._scorer.score(task_text)

        best: ProviderProtocol | None = None
        best_score = -1
        for p in candidates:
            score = len(p.capabilities.capabilities) + p.capabilities.max_context // 100_000
            if score > best_score:
                best_score = score
                best = p

        provider = best or candidates[0]
        model = self._pick_model(provider, difficulty.score)
        return provider, model

    def _route_cost_first(
        self,
        candidates: list[ProviderProtocol],
        messages: list[Message],
    ) -> tuple[ProviderProtocol, str]:
        """Pick the cheapest provider + model combo."""
        task_text = self._extract_task(messages)
        cheapest_cost = float("inf")
        chosen_provider = candidates[0]
        chosen_model = (
            candidates[0].capabilities.models[0] if candidates[0].capabilities.models else ""
        )

        for p in candidates:
            for model_name in p.capabilities.models:
                try:
                    est = self._estimator.estimate_from_text(model_name, task_text)
                    if est.total_cost < cheapest_cost:
                        cheapest_cost = est.total_cost
                        chosen_provider = p
                        chosen_model = model_name
                except KeyError:
                    continue

        return chosen_provider, chosen_model

    def _route_latency_first(
        self,
        candidates: list[ProviderProtocol],
    ) -> tuple[ProviderProtocol, str]:
        """Pick the provider with the smallest model (proxy for low latency)."""
        best: ProviderProtocol | None = None
        best_ctx = float("inf")
        for p in candidates:
            if p.capabilities.max_context < best_ctx:
                best_ctx = p.capabilities.max_context
                best = p
        provider = best or candidates[0]
        model = provider.capabilities.models[0] if provider.capabilities.models else ""
        return provider, model

    def _route_round_robin(
        self,
        candidates: list[ProviderProtocol],
    ) -> tuple[ProviderProtocol, str]:
        """Cycle through providers in order."""
        names = [p.name for p in candidates]
        if self._rr_cycle is None or set(names) != getattr(self, "_rr_names", set()):
            self._rr_cycle = itertools.cycle(names)
            self._rr_names = set(names)
        chosen_name = next(self._rr_cycle)
        provider = next(p for p in candidates if p.name == chosen_name)
        model = provider.capabilities.models[0] if provider.capabilities.models else ""
        return provider, model

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_task(messages: list[Message]) -> str:
        """Get the last user message as a task string."""
        for m in reversed(messages):
            if m.role.value == "user":
                return m.content
        return ""

    @staticmethod
    def _pick_model(provider: ProviderProtocol, difficulty: int) -> str:
        """Pick the first model from the provider's model list.

        A more sophisticated version could match difficulty ranges per model.
        """
        models = provider.capabilities.models
        if not models:
            return ""
        # Simple heuristic: last model is most capable
        if difficulty >= 7 and len(models) > 1:
            return models[-1]
        return models[0]
