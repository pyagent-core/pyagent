"""OpenAIProvider: wraps the OpenAI Python client as a ProviderProtocol."""

from __future__ import annotations

from openai import AsyncOpenAI

from pyagent_patterns.base import Message, Role
from pyagent_providers.base import HealthStatus, ProviderCapabilities
from pyagent_router.selector import Capability


class OpenAIProvider:
    """OpenAI provider implementing ``ProviderProtocol``.

    Requires: ``pip install pyagent-providers[openai]``

    Args:
        api_key: OpenAI API key. Falls back to ``OPENAI_API_KEY`` env var.
        models: Models this provider exposes. Defaults to common GPT models.
        default_model: Model to use when none is specified in ``complete()``.
        name: Provider identifier. Defaults to ``"openai"``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        default_model: str = "gpt-4o-mini",
        name: str = "openai",
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._default_model = default_model
        self._name = name
        self._models = models or [
            "gpt-4.1-nano",
            "gpt-4o-mini",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4.1",
            "o3-mini",
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
            max_context=1_000_000,
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
        """Ping the models endpoint to verify connectivity."""
        try:
            await self._client.models.list()
            return HealthStatus.HEALTHY
        except Exception:
            return HealthStatus.UNHEALTHY

    async def complete(self, messages: list[Message], model: str | None = None) -> str:
        """Generate a completion using the OpenAI Chat API.

        Args:
            messages: Conversation history.
            model: Model override. Uses ``default_model`` if ``None``.

        Returns:
            The assistant response text.
        """
        response = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=[{"role": m.role.value, "content": m.content} for m in messages],
        )
        return response.choices[0].message.content or ""

    async def __call__(self, messages: list[Message]) -> str:
        return await self.complete(messages)
