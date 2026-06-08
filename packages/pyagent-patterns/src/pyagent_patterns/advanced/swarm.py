"""Swarm pattern: emergent behavior from many agents with local rules, no controller.

Each agent operates independently with simple local rules.
Global behavior emerges from agent interactions. No central orchestrator.

LLM calls: N agents x rounds
"""

from __future__ import annotations

import asyncio
import random

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class Swarm(Pattern):
    """Decentralized swarm: agents interact locally, behavior emerges globally.

    Args:
        agents: Pool of swarm agents (all follow same local rules).
        rounds: Number of interaction rounds.
        neighbor_count: How many random peers each agent interacts with per round.
        aggregation: How to produce final output from swarm state.
            "last" = last round's outputs, "vote" = majority vote.
    """

    def __init__(
        self,
        agents: list[Agent],
        rounds: int = 3,
        neighbor_count: int = 2,
        aggregation: str = "last",
    ) -> None:
        if len(agents) < 2:
            raise ValueError("Swarm requires at least 2 agents")
        self._agents = agents
        self._rounds = rounds
        self._neighbor_count = min(neighbor_count, len(agents) - 1)
        self._aggregation = aggregation

    @property
    def pattern_type(self) -> str:
        return "swarm"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        # Initialize each agent's state
        states: dict[str, str] = {}

        # Round 0: each agent independently responds to the task
        init_tasks = [agent.run([Message.user(ctx.task)]) for agent in self._agents]
        init_results = await asyncio.gather(*init_tasks)
        for agent, result in zip(self._agents, init_results, strict=False):
            states[agent.name] = result.content
            messages.append(result)

        # Subsequent rounds: agents interact with random neighbors
        for _round_num in range(1, self._rounds + 1):
            new_states: dict[str, str] = {}

            async def _update_agent(
                agent: Agent, _states: dict[str, str] = states
            ) -> tuple[str, str]:
                # Select random neighbors
                others = [a for a in self._agents if a.name != agent.name]
                neighbors = random.sample(others, min(self._neighbor_count, len(others)))

                neighbor_views = "\n".join(f"- {n.name}: {_states[n.name]}" for n in neighbors)
                prompt = Message.user(
                    f"Task: {ctx.task}\n\n"
                    f"Your current response: {_states[agent.name]}\n\n"
                    f"Neighbor responses:\n{neighbor_views}\n\n"
                    f"Update your response considering your neighbors' views."
                )
                result = await agent.run([prompt])
                return agent.name, result.content

            update_tasks = [_update_agent(agent) for agent in self._agents]
            updates = await asyncio.gather(*update_tasks)
            for name, content in updates:
                new_states[name] = content
                messages.append(Message.assistant(content, name=name))

            states = new_states

        # Aggregate final output
        if self._aggregation == "vote":
            from collections import Counter

            first_lines = [s.split("\n")[0].strip() for s in states.values()]
            winner = Counter(first_lines).most_common(1)[0][0]
            output = winner
        else:
            output = "\n\n".join(f"[{name}]: {content}" for name, content in states.items())

        return Result(
            output=output,
            messages=messages,
            metadata={
                "agents": len(self._agents),
                "rounds": self._rounds,
                "aggregation": self._aggregation,
                "final_states": states,
            },
        )
