"""Streaming support for patterns.

Allows patterns to yield intermediate results as they execute, rather than
waiting for the full result. Useful for real-time UIs and long-running workflows.

Usage:
    async for chunk in stream_pattern(pattern, "task"):
        print(chunk.content, end="", flush=True)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pyagent_patterns.base import Pattern


@dataclass
class StreamChunk:
    """A single chunk of streaming output."""

    content: str
    agent_name: str = ""
    chunk_type: str = "text"  # "text", "stage_complete", "round_complete", "final"
    metadata: dict[str, Any] = field(default_factory=dict)


async def stream_pattern(pattern: Pattern, task: str) -> AsyncIterator[StreamChunk]:
    """Stream a pattern's execution, yielding chunks as they complete.

    For patterns that don't natively support streaming, this wraps the
    full execution and yields the result as a single final chunk.

    For Pipeline patterns, yields after each stage completes.
    For Fan-Out, yields as each parallel agent completes.
    """
    from pyagent_patterns.orchestration.fan_out_fan_in import FanOutFanIn
    from pyagent_patterns.orchestration.pipeline import Pipeline

    if isinstance(pattern, Pipeline):
        async for chunk in _stream_pipeline(pattern, task):
            yield chunk
    elif isinstance(pattern, FanOutFanIn):
        async for chunk in _stream_fanout(pattern, task):
            yield chunk
    else:
        # Fallback: run full pattern and yield result as single chunk
        result = await pattern.run(task)
        yield StreamChunk(
            content=result.output,
            chunk_type="final",
            metadata=result.metadata,
        )


async def _stream_pipeline(pipeline: Pattern, task: str) -> AsyncIterator[StreamChunk]:
    """Stream a pipeline stage by stage."""
    from pyagent_patterns.base import Message, Role

    current_input = task
    for i, stage in enumerate(pipeline._stages):
        messages = [Message(role=Role.USER, content=current_input)]
        if stage.system_prompt:
            messages.insert(0, Message(role=Role.SYSTEM, content=stage.system_prompt))
        response = await stage.llm.generate(messages)
        current_input = response

        is_last = i == len(pipeline._stages) - 1
        yield StreamChunk(
            content=response,
            agent_name=stage.name,
            chunk_type="final" if is_last else "stage_complete",
            metadata={"stage": i, "stage_name": stage.name},
        )


async def _stream_fanout(fanout: Pattern, task: str) -> AsyncIterator[StreamChunk]:
    """Stream fan-out as each parallel agent completes."""
    from pyagent_patterns.base import Message, Role

    queue: asyncio.Queue[StreamChunk | None] = asyncio.Queue()

    async def run_agent(agent, idx: int) -> None:
        messages = [Message(role=Role.USER, content=task)]
        if agent.system_prompt:
            messages.insert(0, Message(role=Role.SYSTEM, content=agent.system_prompt))
        response = await agent.llm.generate(messages)
        await queue.put(
            StreamChunk(
                content=response,
                agent_name=agent.name,
                chunk_type="stage_complete",
                metadata={"agent_index": idx},
            )
        )

    tasks = [asyncio.create_task(run_agent(a, i)) for i, a in enumerate(fanout._agents)]
    done_count = 0
    total = len(tasks)

    while done_count < total:
        chunk = await queue.get()
        if chunk is not None:
            done_count += 1
            yield chunk

    await asyncio.gather(*tasks)

    # Aggregate
    "\n".join(f"[{a.name}]: (see prior chunks)" for a in fanout._agents)
    result = await fanout.run(task)
    yield StreamChunk(
        content=result.output,
        agent_name="aggregator",
        chunk_type="final",
        metadata=result.metadata,
    )
