#!/usr/bin/env python3
"""Contract Review — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.resolution import CrossReflection
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import MAX_ROUNDS, STOP_PHRASE, build_agents

load_dotenv()
log = logging.getLogger(__name__)

DEMO_CLAUSE = (
    "Section 8.2: Either party may terminate this Agreement for convenience upon 30 days written "
    "notice. Upon termination, Customer shall pay all fees incurred through the termination date "
    "plus a termination fee equal to 50% of the remaining contract value."
)


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    review = CrossReflection(
        agents=[agents["counsel"], agents["partner"]],
        max_rounds=MAX_ROUNDS,
        stop_phrase=STOP_PHRASE,
    )
    return BoundedExecution(
        pattern=review,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Review error. Flag clause for manual legal review."),
        max_retries=2,
        timeout_seconds=120.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_review(safe: BoundedExecution, clause: str):
    return await safe.run(clause)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/contract_review_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)
    recorder.start("contract_review")
    result = await run_review(safe, DEMO_CLAUSE)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
