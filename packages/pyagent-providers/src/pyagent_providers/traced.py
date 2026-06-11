"""TracedProvider: thin wrapper that emits trace events for every LLM call."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyagent_patterns.base import Message

    from pyagent_providers.base import HealthStatus, ProviderCapabilities, ProviderProtocol


class TracedProvider:
    """Wrapper that emits trace events for every ``complete()`` / ``__call__`` invocation.

    Wraps any ``ProviderProtocol`` implementation without modifying the original.

    Args:
        provider: The underlying provider to delegate calls to.
        trace_bus: A ``TraceEventBus`` instance (from pyagent-trace).
    """

    def __init__(self, provider: ProviderProtocol, trace_bus: Any) -> None:
        self._provider = provider
        self._trace_bus = trace_bus

    @property
    def name(self) -> str:
        return self._provider.name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._provider.capabilities

    async def health(self) -> HealthStatus:
        return await self._provider.health()

    async def complete(self, messages: list[Message], model: str | None = None) -> str:
        """Delegate to wrapped provider and emit trace events."""
        start = time.time()
        self._emit(
            "provider_call_start",
            {
                "provider": self.name,
                "model": model or "default",
                "input_messages": len(messages),
            },
        )

        try:
            result = await self._provider.complete(messages, model)
        except Exception as exc:
            self._emit(
                "provider_call_error",
                {
                    "provider": self.name,
                    "error": str(exc),
                    "duration_seconds": time.time() - start,
                },
            )
            raise

        duration = time.time() - start
        input_tokens = sum(len(m.content) for m in messages) // 4
        output_tokens = len(result) // 4

        self._emit(
            "provider_call_end",
            {
                "provider": self.name,
                "model": model or "default",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_seconds": duration,
            },
        )

        return result

    async def __call__(self, messages: list[Message]) -> str:
        """LLMCallable-compatible entry point — delegates to ``complete``."""
        return await self.complete(messages)

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit a trace event to the bus."""
        try:
            from pyagent_trace.events import TraceEvent

            self._trace_bus.emit(
                TraceEvent(
                    timestamp=time.time(),
                    event_type=event_type,
                    agent_name=payload.get("provider", ""),
                    payload=payload,
                )
            )
        except Exception:
            pass  # trace must never break provider execution
