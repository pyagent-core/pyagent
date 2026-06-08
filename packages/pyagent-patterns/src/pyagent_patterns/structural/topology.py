"""Topology pattern: configurable communication graph — Chain, Star, or Mesh.

Controls which agents can communicate with which, affecting information
flow, overhead, and result quality.

- Chain: A→B→C (sequential, low overhead)
- Star: Hub↔{A,B,C} (centralized, easy to trace)
- Mesh: A↔B↔C↔A (rich but expensive)
"""

from __future__ import annotations

import asyncio
from enum import StrEnum

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class TopologyType(StrEnum):
    CHAIN = "chain"
    STAR = "star"
    MESH = "mesh"


class Topology(Pattern):
    """Configurable agent communication topology.

    Args:
        agents: List of agents participating in the topology.
        topology: The communication structure (chain, star, mesh).
        hub_index: For star topology, the index of the hub agent. Defaults to 0.
        rounds: For mesh topology, number of communication rounds.
    """

    def __init__(
        self,
        agents: list[Agent],
        topology: TopologyType = TopologyType.CHAIN,
        hub_index: int = 0,
        rounds: int = 1,
    ) -> None:
        if len(agents) < 2:
            raise ValueError("Topology requires at least 2 agents")
        self._agents = agents
        self._topology = topology
        self._hub_index = hub_index
        self._rounds = rounds

    @property
    def pattern_type(self) -> str:
        return f"topology_{self._topology.value}"

    async def _execute(self, ctx: Context) -> Result:
        if self._topology == TopologyType.CHAIN:
            return await self._chain(ctx)
        elif self._topology == TopologyType.STAR:
            return await self._star(ctx)
        else:
            return await self._mesh(ctx)

    async def _chain(self, ctx: Context) -> Result:
        """A→B→C: sequential processing."""
        messages: list[Message] = []
        current = ctx.task

        for agent in self._agents:
            result = await agent.run([Message.user(current)])
            messages.append(result)
            current = result.content

        return Result(output=current, messages=messages, metadata={"topology": "chain"})

    async def _star(self, ctx: Context) -> Result:
        """Hub↔{spokes}: hub collects from all spokes."""
        messages: list[Message] = []
        hub = self._agents[self._hub_index]
        spokes = [a for i, a in enumerate(self._agents) if i != self._hub_index]

        # Spokes process in parallel
        tasks = [spoke.run([Message.user(ctx.task)]) for spoke in spokes]
        spoke_results = await asyncio.gather(*tasks)
        messages.extend(spoke_results)

        # Hub synthesizes
        summary = "\n".join(f"- {spokes[i].name}: {r.content}" for i, r in enumerate(spoke_results))
        hub_result = await hub.run(
            [Message.user(f"Synthesize these inputs:\n{summary}\n\nOriginal task: {ctx.task}")]
        )
        messages.append(hub_result)

        return Result(output=hub_result.content, messages=messages, metadata={"topology": "star"})

    async def _mesh(self, ctx: Context) -> Result:
        """Full mesh: every agent sees every other agent's output per round."""
        messages: list[Message] = []
        outputs = {a.name: "" for a in self._agents}

        # Initial round
        tasks = [a.run([Message.user(ctx.task)]) for a in self._agents]
        initial = await asyncio.gather(*tasks)
        for agent, result in zip(self._agents, initial, strict=False):
            outputs[agent.name] = result.content
            messages.append(result)

        # Subsequent mesh rounds
        for _ in range(1, self._rounds + 1):
            for agent in self._agents:
                peer_outputs = "\n".join(
                    f"- {name}: {content}"
                    for name, content in outputs.items()
                    if name != agent.name
                )
                result = await agent.run(
                    [
                        Message.user(
                            f"Task: {ctx.task}\n\nPeer outputs:\n{peer_outputs}\n\nProvide your updated response."
                        )
                    ]
                )
                outputs[agent.name] = result.content
                messages.append(result)

        # Final output is concatenation of all agent outputs
        final = "\n\n".join(f"[{name}]: {content}" for name, content in outputs.items())
        return Result(
            output=final, messages=messages, metadata={"topology": "mesh", "rounds": self._rounds}
        )
