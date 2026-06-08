"""Core abstractions: Pattern, Agent, Message, Context, Result."""

from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


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
    """

    name: str
    llm: LLMCallable
    system_prompt: str = ""
    description: str = ""

    async def run(self, messages: list[Message]) -> Message:
        """Send messages to the LLM and return an assistant message."""
        call_messages = list(messages)
        if self.system_prompt:
            call_messages.insert(0, Message.system(self.system_prompt))
        content = await self.llm(call_messages)
        return Message.assistant(content, name=self.name)


class Pattern(ABC):
    """Abstract base class for all multi-agent patterns.

    Subclasses must implement `_execute`. The `run` method handles timing,
    context creation, and metadata collection.
    """

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

        start = time.perf_counter()
        result = await self._execute(ctx)
        result.duration_seconds = time.perf_counter() - start
        result.metadata["pattern_type"] = self.pattern_type

        # Rough token estimate: ~4 chars per token
        total_chars = sum(len(m.content) for m in result.messages)
        result.token_estimate = total_chars // 4

        return result

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
