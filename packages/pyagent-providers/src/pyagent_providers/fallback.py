"""FallbackChain: ordered provider list with circuit-breaker integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pyagent_patterns.base import Message
from pyagent_providers.base import HealthStatus, ProviderProtocol

logger = logging.getLogger(__name__)


@dataclass
class FallbackAttempt:
    """Record of a single fallback attempt."""

    provider_name: str
    success: bool
    error: str | None = None


@dataclass
class FallbackResult:
    """Result of a fallback chain execution.

    Attributes:
        output: The completion text from the first successful provider.
        provider_name: Name of the provider that succeeded.
        attempts: Ordered log of every attempt.
    """

    output: str
    provider_name: str
    attempts: list[FallbackAttempt] = field(default_factory=list)


class FallbackChain:
    """Try providers in order until one succeeds.

    Optionally integrates with ``CircuitBreaker`` from ``pyagent-patterns``
    to skip providers whose circuits are open.

    Args:
        providers: Ordered list of providers to try.
        circuit_breakers: Optional mapping of provider name → CircuitBreaker.
            If a provider's circuit is open, it is skipped.
    """

    def __init__(
        self,
        providers: list[ProviderProtocol],
        circuit_breakers: dict[str, Any] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("FallbackChain requires at least one provider")
        self._providers = list(providers)
        self._circuit_breakers = circuit_breakers or {}

    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
    ) -> FallbackResult:
        """Try each provider in order.

        Args:
            messages: Conversation messages.
            model: Optional model override passed to each provider.

        Returns:
            ``FallbackResult`` with the first successful output.

        Raises:
            RuntimeError: If all providers fail.
        """
        attempts: list[FallbackAttempt] = []

        for provider in self._providers:
            # Check circuit breaker
            cb = self._circuit_breakers.get(provider.name)
            if cb is not None:
                from pyagent_patterns.recovery import CircuitState

                if hasattr(cb, "state") and cb.state == CircuitState.OPEN:
                    attempts.append(
                        FallbackAttempt(provider.name, success=False, error="circuit_open")
                    )
                    logger.debug("Skipping %s — circuit open", provider.name)
                    continue

            try:
                output = await provider.complete(messages, model)
                attempts.append(FallbackAttempt(provider.name, success=True))

                # Record success on circuit breaker
                if cb is not None and hasattr(cb, "_on_success"):
                    cb._on_success()

                return FallbackResult(
                    output=output,
                    provider_name=provider.name,
                    attempts=attempts,
                )
            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                attempts.append(
                    FallbackAttempt(provider.name, success=False, error=error_msg)
                )
                logger.warning("Provider %s failed: %s", provider.name, error_msg)

                # Record failure on circuit breaker
                if cb is not None and hasattr(cb, "_on_failure"):
                    cb._on_failure()

        failed_names = [a.provider_name for a in attempts]
        raise RuntimeError(
            f"All providers failed in fallback chain: {failed_names}. "
            f"Errors: {[a.error for a in attempts if a.error]}"
        )

    async def __call__(self, messages: list[Message]) -> str:
        """LLMCallable-compatible interface."""
        result = await self.complete(messages)
        return result.output
