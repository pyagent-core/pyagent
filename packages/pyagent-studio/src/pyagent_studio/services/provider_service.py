"""ProviderService: LiteLLM-backed multi-provider LLM service.

Wraps LiteLLM to give pyagent-studio access to 100+ LLM providers
(OpenAI, Anthropic, Gemini, Ollama, Azure, Bedrock, Mistral, Groq,
DeepSeek, Cohere, Together, vLLM, HuggingFace, Replicate, etc.).
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

try:
    import litellm

    _HAS_LITELLM = True
except ImportError:
    _HAS_LITELLM = False
    litellm = None  # type: ignore[assignment]


class ProviderService:
    """LiteLLM-backed multi-provider LLM service.

    Usage:
        svc = ProviderService()
        response = await svc.complete("gpt-4o", [{"role": "user", "content": "Hello"}])
        async for chunk in svc.stream("gpt-4o", [{"role": "user", "content": "Hello"}]):
            print(chunk, end="")
    """

    def __init__(self, default_model: str = "gpt-4o") -> None:
        if not _HAS_LITELLM:
            raise ImportError(
                "litellm package not installed. Install with: pip install litellm"
            )
        self._default_model = default_model

    @property
    def name(self) -> str:
        """Provider name."""
        return "litellm"

    async def complete(
        self,
        model: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a completion via LiteLLM.

        Args:
            model: Model identifier (e.g. "gpt-4o", "claude-3-sonnet").
            messages: Conversation messages in OpenAI format.
            **kwargs: Additional LiteLLM parameters.

        Returns:
            The assistant response text.
        """
        model = model or self._default_model
        messages = messages or []
        response = await litellm.acompletion(model=model, messages=messages, **kwargs)
        return response.choices[0].message.content or ""

    async def stream(
        self,
        model: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a completion via LiteLLM.

        Args:
            model: Model identifier.
            messages: Conversation messages in OpenAI format.
            **kwargs: Additional LiteLLM parameters.

        Yields:
            Text chunks as they arrive.
        """
        model = model or self._default_model
        messages = messages or []
        response = await litellm.acompletion(
            model=model, messages=messages, stream=True, **kwargs
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    def list_models(self) -> list[str]:
        """List available models from LiteLLM's model registry.

        Returns:
            List of model identifiers.
        """
        try:
            model_list = getattr(litellm, "model_list", None)
            if model_list:
                return list(model_list)
            models_by_provider = getattr(litellm, "models_by_provider", None)
            if models_by_provider:
                return list(models_by_provider.keys())
            return []
        except Exception:
            return []

    async def health_check(self, model: str | None = None) -> dict[str, Any]:
        """Check if a model endpoint is reachable.

        Args:
            model: Model to check. Uses default if None.

        Returns:
            Dict with 'healthy' bool and optional 'error' string.
        """
        model = model or self._default_model
        try:
            await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return {"healthy": True, "model": model}
        except Exception as exc:
            return {"healthy": False, "model": model, "error": str(exc)}

    def model_cost(self, model: str | None = None) -> dict[str, float]:
        """Get cost per token for a model from LiteLLM's cost tables.

        Args:
            model: Model identifier.

        Returns:
            Dict with 'input_cost_per_token' and 'output_cost_per_token'.
        """
        model = model or self._default_model
        try:
            cost_info = litellm.get_model_cost_map(url="")
            if model in cost_info:
                info = cost_info[model]
                return {
                    "input_cost_per_token": info.get("input_cost_per_token", 0.0),
                    "output_cost_per_token": info.get("output_cost_per_token", 0.0),
                }
        except Exception:
            pass
        return {"input_cost_per_token": 0.0, "output_cost_per_token": 0.0}
