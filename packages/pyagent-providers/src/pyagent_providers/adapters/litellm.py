"""LiteLLMProvider: wraps LiteLLM as a ProviderProtocol (100+ model providers)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import litellm
from pyagent_router.selector import Capability

from pyagent_providers.base import HealthStatus, ProviderCapabilities

if TYPE_CHECKING:
    from pyagent_patterns.base import Message


class LiteLLMProvider:
    """LiteLLM provider implementing ``ProviderProtocol``.

    LiteLLM proxies 100+ model providers (OpenAI, Anthropic, Gemini, Ollama,
    Bedrock, Azure, etc.) through a unified interface.

    Requires: ``pip install pyagent-providers[litellm]``

    Args:
        models: List of LiteLLM model strings this provider exposes.
        default_model: Model to use when none is specified.
        name: Provider identifier. Defaults to ``"litellm"``.
        capabilities: Capability set. Defaults to broad general capabilities.
        max_context: Max context window.
    """

    def __init__(
        self,
        models: list[str] | None = None,
        default_model: str = "gpt-4o-mini",
        name: str = "litellm",
        capabilities: set[Capability] | None = None,
        max_context: int = 128_000,
    ) -> None:
        self._default_model = default_model
        self._name = name
        self._models = models or [
            "gpt-4o-mini",
            "gpt-4o",
            "anthropic/claude-sonnet-4-20250514",
            "gemini/gemini-2.5-flash",
        ]
        self._capabilities = ProviderCapabilities(
            models=self._models,
            capabilities=capabilities
            or {Capability.GENERAL, Capability.CODE, Capability.REASONING},
            max_context=max_context,
            supports_streaming=True,
            supports_tools=True,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def health(self) -> HealthStatus:
        """Verify LiteLLM can reach at least one provider."""
        try:
            await litellm.acompletion(
                model=self._default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return HealthStatus.HEALTHY
        except Exception:
            return HealthStatus.DEGRADED

    async def complete(self, messages: list[Message], model: str | None = None) -> str:
        """Generate a completion using LiteLLM's unified API.

        Args:
            messages: Conversation history.
            model: LiteLLM model string override. Uses ``default_model`` if ``None``.

        Returns:
            The assistant response text.
        """
        response = await litellm.acompletion(
            model=model or self._default_model,
            messages=[{"role": m.role.value, "content": m.content} for m in messages],
        )
        return response.choices[0].message.content or ""

    async def __call__(self, messages: list[Message]) -> str:
        return await self.complete(messages)
