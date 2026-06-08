"""CompressMiddleware: inject compression between pattern stages.

Wraps agents so that their outputs are automatically compressed
before being passed to the next agent, reducing inter-agent token transfer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyagent_patterns.base import Agent, Message

from pyagent_compress.compressor import MessageCompressor

if TYPE_CHECKING:
    from pyagent_compress.budget import TokenBudget


class CompressedAgent(Agent):
    """Agent wrapper that compresses output messages.

    Args:
        agent: The original agent.
        compressor: MessageCompressor instance.
        budget: Optional TokenBudget for tracking.
    """

    def __init__(
        self,
        agent: Agent,
        compressor: MessageCompressor,
        budget: TokenBudget | None = None,
    ) -> None:
        super().__init__(
            name=agent.name,
            llm=agent.llm,
            system_prompt=agent.system_prompt,
            description=agent.description,
        )
        self._original = agent
        self._compressor = compressor
        self._budget = budget
        self.compression_log: list[dict[str, int | float]] = []

    async def run(self, messages: list[Message]) -> Message:
        """Run the agent and compress the output."""
        result = await self._original.run(messages)

        # Compress the output
        compressed = self._compressor.compress(result.content)
        self.compression_log.append(
            {
                "original_tokens": compressed.original_tokens,
                "compressed_tokens": compressed.compressed_tokens,
                "savings_pct": compressed.savings_pct,
            }
        )

        # Track budget if available
        if self._budget:
            self._budget.consume(self._original.name, compressed.compressed_tokens)

        return Message(
            role=result.role,
            content=compressed.compressed,
            name=result.name,
            metadata={
                **result.metadata,
                "compressed": True,
                "original_tokens": compressed.original_tokens,
                "compressed_tokens": compressed.compressed_tokens,
                "savings_pct": compressed.savings_pct,
            },
        )


class CompressMiddleware:
    """Middleware that wraps agents with automatic output compression.

    Usage:
        middleware = CompressMiddleware(target_ratio=0.5)
        compressed_agent = middleware.wrap(my_agent)

    Args:
        compressor: Optional MessageCompressor. Created with defaults if None.
        budget: Optional TokenBudget for workflow-wide tracking.
        target_ratio: Target compression ratio (used if compressor not provided).
    """

    def __init__(
        self,
        compressor: MessageCompressor | None = None,
        budget: TokenBudget | None = None,
        target_ratio: float = 0.5,
    ) -> None:
        self._compressor = compressor or MessageCompressor(target_ratio=target_ratio)
        self._budget = budget

    def wrap(self, agent: Agent) -> CompressedAgent:
        """Wrap an agent with compression."""
        return CompressedAgent(
            agent=agent,
            compressor=self._compressor,
            budget=self._budget,
        )

    def wrap_all(self, agents: list[Agent]) -> list[CompressedAgent]:
        """Wrap multiple agents."""
        return [self.wrap(a) for a in agents]
