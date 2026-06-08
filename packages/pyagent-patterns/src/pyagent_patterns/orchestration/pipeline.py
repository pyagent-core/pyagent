"""Pipeline pattern: sequential chain of agents where each stage's output feeds the next.

Each agent processes the output of the previous stage.
Ideal for document processing, ETL, and multi-step transformations.

LLM calls: N (one per stage)
"""

from __future__ import annotations

from typing import AsyncIterator

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class Pipeline(Pattern):
    """Sequential stage chain — output of stage N becomes input of stage N+1.

    Args:
        stages: Ordered list of agents, each processing the previous output.
    """

    def __init__(self, stages: list[Agent]) -> None:
        if not stages:
            raise ValueError("Pipeline requires at least one stage")
        self._stages = stages

    @property
    def pattern_type(self) -> str:
        return "pipeline"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        current_input = ctx.task

        for i, stage in enumerate(self._stages):
            stage_msg = Message.user(current_input)
            response = await stage.run([stage_msg])
            messages.append(response)
            current_input = response.content

        return Result(
            output=current_input,
            messages=messages,
            metadata={"stages": len(self._stages), "stage_names": [s.name for s in self._stages]},
        )

    async def stream(self, task: str, context: Context | None = None) -> AsyncIterator[str]:
        """Stream stage completions as they finish."""
        ctx = context or Context(task=task)
        current_input = task

        for i, stage in enumerate(self._stages):
            stage_msg = Message.user(current_input)
            response = await stage.run([stage_msg])
            current_input = response.content
            yield f"[Stage {i + 1}/{len(self._stages)} — {stage.name}] {current_input}"
