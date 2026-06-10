"""AnthropicProvider: wraps the Anthropic Python client as a ProviderProtocol."""

from __future__ import annotations

import anthropic

from pyagent_patterns.base import Message, Role
from pyagent_providers.base import HealthStatus, ProviderCapabilities
from pyagent_router.selector import Capability


class AnthropicProvider:
    """Anthropic provider implementing ``ProviderProtocol``.

    Requires: ``pip install pyagent-providers[anthropic]``

    Args:
        api_key: Anthropic API key. Falls back to ``ANTHROPIC_API_KEY`` env var.
        models: Models this provider exposes.
        default_model: Model to use when none is specified.
        name: Provider identifier. Defaults to ``"anthropic"``.
        max_tokens: Default max tokens for completions.
    """

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        default_model: str = "claude-sonnet-4-20250514",
        name: str = "anthropic",
        max_tokens: int = 4096,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._default_model = default_model
        self._name = name
        self._max_tokens = max_tokens
        self._models = models or [
            "claude-haiku-3-5-20241022",
            "claude-sonnet-4-20250514",
        ]
        self._capabilities = ProviderCapabilities(
            models=self._models,
            capabilities={
                Capability.GENERAL,
                Capability.CODE,
                Capability.REASONING,
                Capability.CREATIVE,
                Capability.VISION,
            },
            max_context=200_000,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def health(self) -> HealthStatus:
        """Check connectivity by counting available tokens (lightweight call)."""
        try:
            await self._client.messages.count_tokens(
                model=self._default_model,
                messages=[{"role": "user", "content": "ping"}],
            )
            return HealthStatus.HEALTHY
        except Exception:
            return HealthStatus.UNHEALTHY

    async def complete(self, messages: list[Message], model: str | None = None) -> str:
        """Generate a completion using the Anthropic Messages API.

        Anthropic requires system messages to be passed separately from the
        conversation history.

        Args:
            messages: Conversation history.
            model: Model override. Uses ``default_model`` if ``None``.

        Returns:
            The assistant response text.
        """
        system = next(
            (m.content for m in messages if m.role == Role.SYSTEM),
            "You are a helpful assistant.",
        )
        chat_msgs = [
            {"role": m.role.value, "content": m.content}
            for m in messages
            if m.role != Role.SYSTEM
        ]
        response = await self._client.messages.create(
            model=model or self._default_model,
            max_tokens=self._max_tokens,
            system=system,
            messages=chat_msgs,
        )
        return response.content[0].text

    async def __call__(self, messages: list[Message]) -> str:
        return await self.complete(messages)
