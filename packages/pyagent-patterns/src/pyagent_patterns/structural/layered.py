"""Layered Cooperation pattern: agents organized into hierarchical abstraction layers.

Each layer processes the output of the previous layer at a different level
of abstraction. Layer 1 gathers data, Layer 2 analyzes, Layer 3 synthesizes.

LLM calls: sum of agents across all layers
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


@dataclass
class Layer:
    """A named layer containing one or more parallel agents."""

    name: str
    agents: list[Agent]


class Layered(Pattern):
    """Hierarchical layers of agents with increasing abstraction.

    Args:
        layers: Ordered list of layers from bottom (data) to top (synthesis).
    """

    def __init__(self, layers: list[Layer]) -> None:
        if not layers:
            raise ValueError("Layered requires at least one layer")
        self._layers = layers

    @property
    def pattern_type(self) -> str:
        return "layered"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        layer_input = ctx.task

        for _i, layer in enumerate(self._layers):
            # Run all agents in this layer in parallel
            tasks = [agent.run([Message.user(layer_input)]) for agent in layer.agents]
            layer_results = await asyncio.gather(*tasks)
            messages.extend(layer_results)

            # Combine layer output as input for next layer
            if len(layer_results) == 1:
                layer_input = layer_results[0].content
            else:
                layer_input = "\n\n".join(
                    f"[{layer.agents[j].name}]: {r.content}" for j, r in enumerate(layer_results)
                )

        return Result(
            output=layer_input,
            messages=messages,
            metadata={
                "layer_count": len(self._layers),
                "layer_names": [layer_.name for layer_ in self._layers],
                "agents_per_layer": [len(layer_.agents) for layer_ in self._layers],
            },
        )
