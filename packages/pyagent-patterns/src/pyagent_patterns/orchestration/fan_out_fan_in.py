"""Fan-Out / Fan-In pattern: broadcast task to N agents in parallel, aggregate results.

All agents receive the same task and run concurrently. An aggregator
combines their outputs into a unified response.

LLM calls: N agents (parallel) + 1 aggregator = N+1 total
Wall-clock latency: max(agent latencies) + aggregator
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class FanOutFanIn(Pattern):
    """Parallel execution with result aggregation.

    Args:
        agents: List of agents to run in parallel on the same task.
        aggregator: Agent that combines all parallel outputs into one.
    """

    def __init__(self, agents: list[Agent], aggregator: Agent) -> None:
        if not agents:
            raise ValueError("FanOutFanIn requires at least one agent")
        self._agents = agents
        self._aggregator = aggregator

    @property
    def pattern_type(self) -> str:
        return "fan_out_fan_in"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []

        # Fan-out: run all agents in parallel
        tasks = [agent.run(ctx.messages) for agent in self._agents]
        parallel_results = await asyncio.gather(*tasks)
        messages.extend(parallel_results)

        # Fan-in: aggregate results
        combined = "\n\n".join(
            f"--- {self._agents[i].name} ---\n{r.content}"
            for i, r in enumerate(parallel_results)
        )
        agg_prompt = Message.user(
            f"Combine the following analyses into a unified response:\n\n{combined}"
        )
        aggregated = await self._aggregator.run([agg_prompt])
        messages.append(aggregated)

        return Result(
            output=aggregated.content,
            messages=messages,
            metadata={
                "parallel_agents": len(self._agents),
                "agent_names": [a.name for a in self._agents],
            },
        )

    async def stream(self, task: str, context: Context | None = None) -> AsyncIterator[str]:
        """Stream individual agent results as they complete."""
        ctx = context or Context(task=task)
        ctx.messages.append(Message.user(task))

        async def _run_one(agent: Agent) -> tuple[str, str]:
            result = await agent.run(ctx.messages)
            return agent.name, result.content

        tasks = [_run_one(agent) for agent in self._agents]
        for coro in asyncio.as_completed(tasks):
            name, content = await coro
            yield f"[{name}] {content}"
