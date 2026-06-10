"""TraceEvent and TraceEventBus — the contract between trace producers and consumers.

TraceEvent is the universal event format emitted by all pyagent trace producers
(Recorder, CostTracker, @traced_pattern, @traced_agent). TraceEventBus is a
lightweight pub/sub bus that decouples producers from consumers (Studio, exporters).
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class TraceEvent:
    """Contract: every trace event pyagent emits.

    Attributes:
        timestamp: Unix timestamp of the event.
        event_type: One of pattern_start, pattern_end, agent_start, agent_end,
            llm_call, llm_response, routing_decision, compression, error, cost_record.
        agent_name: Name of the agent involved (empty string if N/A).
        pattern_type: Name of the pattern involved (empty string if N/A).
        payload: Event-specific data (tokens, cost, duration, model, messages, etc.).
    """

    timestamp: float
    event_type: str
    agent_name: str = ""
    pattern_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


class TraceEventBus:
    """Pub/sub event bus — the contract between trace producers and studio consumers.

    Usage:
        bus = TraceEventBus()
        sub_id = bus.subscribe(lambda event: print(event))
        bus.emit(TraceEvent(timestamp=time.time(), event_type="llm_call", ...))
        bus.unsubscribe(sub_id)
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, Callable[[TraceEvent], None]] = {}
        self._filtered_subscribers: dict[str, tuple[set[str], Callable[[TraceEvent], None]]] = {}

    def subscribe(self, callback: Callable[[TraceEvent], None]) -> str:
        """Subscribe to all trace events. Returns subscription ID."""
        sub_id = uuid.uuid4().hex
        self._subscribers[sub_id] = callback
        return sub_id

    def subscribe_filter(
        self, event_types: set[str], callback: Callable[[TraceEvent], None]
    ) -> str:
        """Subscribe to specific event types only. Returns subscription ID."""
        sub_id = uuid.uuid4().hex
        self._filtered_subscribers[sub_id] = (event_types, callback)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscription by ID."""
        self._subscribers.pop(subscription_id, None)
        self._filtered_subscribers.pop(subscription_id, None)

    def emit(self, event: TraceEvent) -> None:
        """Emit event to all matching subscribers (sync)."""
        for callback in self._subscribers.values():
            callback(event)
        for event_types, callback in self._filtered_subscribers.values():
            if event.event_type in event_types:
                callback(event)

    async def emit_async(self, event: TraceEvent) -> None:
        """Emit event to all matching subscribers, awaiting any coroutine callbacks."""
        for callback in self._subscribers.values():
            result = callback(event)
            if asyncio.iscoroutine(result):
                await result
        for event_types, callback in self._filtered_subscribers.values():
            if event.event_type in event_types:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    await result
