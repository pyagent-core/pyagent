"""Core abstractions: Pattern, Agent, Message, Context, Result."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class Role(StrEnum):
    """Well-known agent roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class Message:
    """A single message in an agent conversation.

    Attributes:
        role: The sender role (system, user, assistant, tool).
        content: The text content of the message.
        name: Optional agent name for multi-agent conversations.
        metadata: Arbitrary key-value metadata attached to the message.
    """

    role: Role
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def system(cls, content: str, **kw: Any) -> Message:
        return cls(role=Role.SYSTEM, content=content, **kw)

    @classmethod
    def user(cls, content: str, **kw: Any) -> Message:
        return cls(role=Role.USER, content=content, **kw)

    @classmethod
    def assistant(cls, content: str, name: str | None = None, **kw: Any) -> Message:
        return cls(role=Role.ASSISTANT, content=content, name=name, **kw)


@runtime_checkable
class LLMCallable(Protocol):
    """Protocol for any LLM backend — sync or async."""

    async def __call__(self, messages: list[Message]) -> str: ...


class MockLLM:
    """A mock LLM for testing that echoes or returns canned responses.

    Args:
        responses: If provided, returns these in order (cycling). Otherwise echoes last user message.
        delay: Simulated latency in seconds.
    """

    def __init__(self, responses: list[str] | None = None, delay: float = 0.0) -> None:
        self._responses = responses or []
        self._index = 0
        self._delay = delay
        self.call_count = 0
        self.call_log: list[list[Message]] = []

    async def __call__(self, messages: list[Message]) -> str:
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        self.call_count += 1
        self.call_log.append(list(messages))
        if self._responses:
            resp = self._responses[self._index % len(self._responses)]
            self._index += 1
            return resp
        # Echo the last user message
        for msg in reversed(messages):
            if msg.role == Role.USER:
                return f"[MockLLM] Echo: {msg.content}"
        return "[MockLLM] No user message found"


@dataclass
class Context:
    """Shared execution context for a pattern run.

    Attributes:
        task: The original user task/prompt.
        messages: Accumulated message history.
        metadata: Arbitrary shared state across agents.
        parent_id: ID of the parent context (for nested patterns).
    """

    task: str
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    _id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def id(self) -> str:
        return self._id

    def child(self, task: str | None = None) -> Context:
        """Create a child context for nested pattern execution."""
        return Context(
            task=task or self.task,
            metadata=dict(self.metadata),
            parent_id=self._id,
        )


@dataclass
class Result:
    """Outcome of a pattern execution.

    Attributes:
        output: The final output text.
        messages: All messages generated during execution.
        metadata: Pattern-specific metadata (rounds, consensus, votes, etc.).
        duration_seconds: Wall-clock execution time.
        token_estimate: Rough estimate of total tokens consumed.
        cost_estimate: Rough estimate of total cost in USD.
    """

    output: str
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    token_estimate: int = 0
    cost_estimate: float = 0.0


@dataclass
class Agent:
    """An LLM-backed agent with a name, system prompt, and callable.

    Args:
        name: Human-readable agent name.
        llm: The LLM callable to use for this agent.
        system_prompt: Optional system prompt prepended to every call.
        description: Description of the agent's purpose (for routing/selection).

    Optional hooks (set via setter methods — no constructor change):
        _trace_bus: Emit agent_start/agent_end trace events.
        _context_ledger: Read context before LLM call; write output after.
        _compressor: Compress agent output before returning.
        _cost_tracker: Record cost per LLM call.
    """

    name: str
    llm: LLMCallable
    system_prompt: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        self._trace_bus: Any = None
        self._context_ledger: Any = None
        self._compressor: Any = None
        self._cost_tracker: Any = None

    # -- Hook setters (return self for chaining) --

    def set_trace_bus(self, bus: Any) -> Agent:
        """Attach a TraceEventBus — emits agent_start/agent_end events on run()."""
        self._trace_bus = bus
        return self

    def set_context(self, ledger: Any) -> Agent:
        """Attach a ContextLedger — reads context before LLM, writes output after."""
        self._context_ledger = ledger
        return self

    def set_compressor(self, compressor: Any) -> Agent:
        """Attach a MessageCompressor — compresses output before returning."""
        self._compressor = compressor
        return self

    def set_cost_tracker(self, tracker: Any) -> Agent:
        """Attach a CostTracker — records cost after each LLM call."""
        self._cost_tracker = tracker
        return self

    async def run(self, messages: list[Message]) -> Message:
        """Send messages to the LLM and return an assistant message.

        When hooks are wired the execution order is:
        1. Emit ``agent_start`` trace event
        2. Prepend context from ledger as messages
        3. Call LLM
        4. Record cost
        5. Compress output
        6. Write result to context ledger
        7. Emit ``agent_end`` trace event with timing/tokens
        """
        start = time.perf_counter()

        # 1. Trace: agent_start
        if self._trace_bus is not None:
            self._emit_trace("agent_start", {})

        # 2. Context: prepend context messages
        call_messages = list(messages)
        if self._context_ledger is not None:
            try:
                ctx_messages = self._context_ledger.to_messages(max_tokens=None)
                if ctx_messages:
                    call_messages = ctx_messages + call_messages
            except Exception:
                logger.debug("Agent '%s': failed to read context ledger", self.name)

        if self.system_prompt:
            call_messages.insert(0, Message.system(self.system_prompt))

        # 3. Call LLM
        content = await self.llm(call_messages)

        # 4. Cost tracking
        if self._cost_tracker is not None:
            try:
                input_tokens = sum(len(m.content) for m in call_messages) // 4
                output_tokens = len(content) // 4
                self._cost_tracker.record(
                    pattern_type="agent",
                    agent_name=self.name,
                    model=getattr(self.llm, "_model", "unknown"),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=0.0,  # real cost comes from provider
                )
            except Exception:
                logger.debug("Agent '%s': failed to record cost", self.name)

        # 5. Compression
        compression_meta: dict[str, Any] = {}
        if self._compressor is not None:
            try:
                compressed = self._compressor.compress(content)
                compression_meta = {
                    "compressed": True,
                    "original_tokens": compressed.original_tokens,
                    "compressed_tokens": compressed.compressed_tokens,
                    "savings_pct": compressed.savings_pct,
                }
                content = compressed.compressed
                # Emit compression trace event
                if self._trace_bus is not None and compressed.savings_pct > 0:
                    self._emit_trace(
                        "compression",
                        {
                            "original_tokens": compressed.original_tokens,
                            "compressed_tokens": compressed.compressed_tokens,
                            "savings_pct": compressed.savings_pct,
                        },
                    )
            except Exception:
                logger.debug("Agent '%s': compression failed, using original", self.name)

        # 6. Context: write output
        if self._context_ledger is not None:
            try:
                from pyagent_context.item import ContextItem, TrustLevel

                self._context_ledger.append(
                    ContextItem(
                        content=content,
                        source=self.name,
                        trust_level=TrustLevel.INFERRED,
                    )
                )
                # Emit context_update trace event
                if self._trace_bus is not None:
                    self._emit_trace(
                        "context_update",
                        {
                            "source": self.name,
                            "tokens": len(content) // 4,
                        },
                    )
            except Exception:
                logger.debug("Agent '%s': failed to write context", self.name)

        duration = time.perf_counter() - start

        # 7. Trace: agent_end
        if self._trace_bus is not None:
            self._emit_trace(
                "agent_end",
                {
                    "duration_seconds": duration,
                    "output_tokens": len(content) // 4,
                    **compression_meta,
                },
            )

        return Message.assistant(content, name=self.name, metadata=compression_meta)

    def _emit_trace(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit a trace event to the attached bus (no-op if bus is None)."""
        try:
            from pyagent_trace.events import TraceEvent

            self._trace_bus.emit(
                TraceEvent(
                    timestamp=time.time(),
                    event_type=event_type,
                    agent_name=self.name,
                    payload=payload,
                )
            )
        except Exception:
            pass  # trace must never break agent execution


class Pattern(ABC):
    """Abstract base class for all multi-agent patterns.

    Subclasses must implement `_execute`. The `run` method handles timing,
    context creation, and metadata collection.

    Optional hooks:
        _trace_bus: Emit pattern_start/pattern_end trace events.
    """

    _trace_bus: Any = None

    def set_trace_bus(self, bus: Any) -> Pattern:
        """Attach a TraceEventBus — emits pattern_start/pattern_end on run()."""
        self._trace_bus = bus
        return self

    @property
    @abstractmethod
    def pattern_type(self) -> str:
        """Return the pattern type name (e.g., 'supervisor', 'debate')."""
        ...

    async def run(self, task: str, context: Context | None = None) -> Result:
        """Execute the pattern on the given task.

        Args:
            task: The user task or prompt.
            context: Optional existing context. Created automatically if None.

        Returns:
            Result with output, messages, metadata, timing, and cost estimates.
        """
        ctx = context or Context(task=task)
        ctx.messages.append(Message.user(task))

        # Trace: pattern_start
        if self._trace_bus is not None:
            self._emit_pattern_trace("pattern_start", {})

        start = time.perf_counter()
        result = await self._execute(ctx)
        result.duration_seconds = time.perf_counter() - start
        result.metadata["pattern_type"] = self.pattern_type

        # Rough token estimate: ~4 chars per token
        total_chars = sum(len(m.content) for m in result.messages)
        result.token_estimate = total_chars // 4

        # Trace: pattern_end
        if self._trace_bus is not None:
            self._emit_pattern_trace(
                "pattern_end",
                {
                    "duration_seconds": result.duration_seconds,
                    "token_estimate": result.token_estimate,
                    "output_length": len(result.output),
                },
            )

        return result

    def _emit_pattern_trace(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit a trace event to the attached bus."""
        try:
            from pyagent_trace.events import TraceEvent

            self._trace_bus.emit(
                TraceEvent(
                    timestamp=time.time(),
                    event_type=event_type,
                    pattern_type=self.pattern_type,
                    payload=payload,
                )
            )
        except Exception:
            pass  # trace must never break pattern execution

    @abstractmethod
    async def _execute(self, ctx: Context) -> Result:
        """Implement the pattern logic. Called by `run`."""
        ...

    async def stream(self, task: str, context: Context | None = None) -> AsyncIterator[str]:
        """Stream partial results as they become available.

        Default implementation runs the full pattern and yields the result.
        Subclasses can override for true streaming.
        """
        result = await self.run(task, context)
        yield result.output
