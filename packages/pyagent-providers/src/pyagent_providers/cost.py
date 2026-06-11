"""CostOptimizer: multi-provider cost comparison wrapping CostEstimator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyagent_router.estimator import CostEstimate, CostEstimator

if TYPE_CHECKING:
    from pyagent_providers.base import ProviderProtocol
    from pyagent_providers.registry import ProviderRegistry


@dataclass(frozen=True)
class ProviderCostEstimate:
    """Cost estimate for a specific provider + model pair.

    Attributes:
        provider_name: Provider that would serve this request.
        model: Model within that provider.
        estimate: The underlying cost estimate.
    """

    provider_name: str
    model: str
    estimate: CostEstimate


class CostOptimizer:
    """Compare costs across all registered providers.

    Wraps ``CostEstimator`` from ``pyagent-router`` and iterates over every
    provider's model list to find the cheapest option.

    Args:
        registry: Provider registry to draw models from.
        cost_estimator: Optional ``CostEstimator`` instance.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        cost_estimator: CostEstimator | None = None,
    ) -> None:
        self._registry = registry
        self._estimator = cost_estimator or CostEstimator()

    def compare(
        self,
        task: str,
        *,
        healthy_only: bool = True,
        limit: int = 10,
    ) -> list[ProviderCostEstimate]:
        """Estimate cost for every provider + model pair and rank cheapest first.

        Args:
            task: The task text to estimate.
            healthy_only: If ``True`` (default), only include healthy providers.
            limit: Maximum number of results to return.

        Returns:
            Sorted list of ``ProviderCostEstimate`` objects, cheapest first.
        """
        candidates = self._registry.discover(healthy_only=healthy_only)
        results: list[ProviderCostEstimate] = []

        for provider in candidates:
            for model_name in provider.capabilities.models:
                try:
                    est = self._estimator.estimate_from_text(model_name, task)
                    results.append(
                        ProviderCostEstimate(
                            provider_name=provider.name,
                            model=model_name,
                            estimate=est,
                        )
                    )
                except KeyError:
                    continue

        results.sort(key=lambda x: x.estimate.total_cost)
        return results[:limit]

    def cheapest(
        self,
        task: str,
        *,
        healthy_only: bool = True,
    ) -> ProviderCostEstimate | None:
        """Return the single cheapest provider + model for a task.

        Returns:
            The cheapest option, or ``None`` if no estimates could be computed.
        """
        estimates = self.compare(task, healthy_only=healthy_only, limit=1)
        return estimates[0] if estimates else None

    def cheapest_provider(
        self,
        task: str,
        *,
        healthy_only: bool = True,
    ) -> tuple[ProviderProtocol, str] | None:
        """Return the cheapest provider object + model name.

        Convenience method for passing directly to ``Agent`` or patterns.
        """
        est = self.cheapest(task, healthy_only=healthy_only)
        if est is None:
            return None
        provider = self._registry.get(est.provider_name)
        if provider is None:
            return None
        return provider, est.model
