"""ProviderRegistry: register, discover, and health-check providers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from pyagent_providers.base import HealthStatus, ProviderInfo, ProviderProtocol
from pyagent_router.selector import Capability


class ProviderRegistry:
    """Central registry of all available LLM providers.

    Supports registration, discovery by capability, and periodic health checks.

    Args:
        auto_health_check: If ``True``, run a health check on registration.
    """

    def __init__(self, *, auto_health_check: bool = False) -> None:
        self._providers: dict[str, ProviderProtocol] = {}
        self._health_cache: dict[str, HealthStatus] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._auto_health_check = auto_health_check

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register(
        self,
        provider: ProviderProtocol,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a provider.

        Args:
            provider: Any object satisfying ``ProviderProtocol``.
            metadata: Optional extra metadata (region, version, etc.).
        """
        self._providers[provider.name] = provider
        self._metadata[provider.name] = metadata or {}
        if self._auto_health_check:
            self._health_cache[provider.name] = await provider.health()
        else:
            self._health_cache[provider.name] = HealthStatus.HEALTHY

    def register_sync(
        self,
        provider: ProviderProtocol,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Synchronous registration (skips health check)."""
        self._providers[provider.name] = provider
        self._metadata[provider.name] = metadata or {}
        self._health_cache[provider.name] = HealthStatus.HEALTHY

    def remove(self, name: str) -> None:
        """Remove a provider by name."""
        self._providers.pop(name, None)
        self._health_cache.pop(name, None)
        self._metadata.pop(name, None)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get(self, name: str) -> ProviderProtocol | None:
        """Look up a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> list[ProviderInfo]:
        """Return info snapshots for all registered providers."""
        return [
            ProviderInfo(
                name=p.name,
                capabilities=p.capabilities,
                health=self._health_cache.get(p.name, HealthStatus.HEALTHY),
                metadata=self._metadata.get(p.name, {}),
            )
            for p in self._providers.values()
        ]

    def discover(
        self,
        required_capabilities: set[Capability] | None = None,
        *,
        healthy_only: bool = True,
    ) -> list[ProviderProtocol]:
        """Find providers matching capability and health requirements.

        Args:
            required_capabilities: If given, only return providers whose
                capabilities are a superset of this set.
            healthy_only: If ``True`` (default), exclude unhealthy providers.

        Returns:
            List of matching providers.
        """
        results: list[ProviderProtocol] = []
        for p in self._providers.values():
            if healthy_only and self._health_cache.get(p.name) == HealthStatus.UNHEALTHY:
                continue
            if required_capabilities and not required_capabilities.issubset(p.capabilities.capabilities):
                continue
            results.append(p)
        return results

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def check_health(self, name: str | None = None) -> dict[str, HealthStatus]:
        """Run health checks.

        Args:
            name: If given, check only this provider. Otherwise check all.

        Returns:
            Mapping of provider name → health status.
        """
        targets = (
            {name: self._providers[name]} if name and name in self._providers else dict(self._providers)
        )

        async def _check(n: str, p: ProviderProtocol) -> tuple[str, HealthStatus]:
            try:
                status = await p.health()
            except Exception:
                status = HealthStatus.UNHEALTHY
            return n, status

        results = await asyncio.gather(*[_check(n, p) for n, p in targets.items()])
        for n, status in results:
            self._health_cache[n] = status
        return dict(results)

    async def remove_unhealthy(self) -> list[str]:
        """Run health checks and remove all unhealthy providers.

        Returns:
            List of removed provider names.
        """
        statuses = await self.check_health()
        removed: list[str] = []
        for name, status in statuses.items():
            if status == HealthStatus.UNHEALTHY:
                self.remove(name)
                removed.append(name)
        return removed

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        return name in self._providers

    def __len__(self) -> int:
        return len(self._providers)
