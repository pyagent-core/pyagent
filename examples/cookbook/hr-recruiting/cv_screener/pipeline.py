#!/usr/bin/env python3
"""CV Screener — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents

load_dotenv()
log = logging.getLogger(__name__)

DEMO_CV = (
    "Senior Backend Engineer, 7 yrs. Built a payments platform handling 4k TPS (Python, Postgres, Kafka). "
    "Led a 5-person team; cut p99 latency 40%. Open-source: maintainer of a popular asyncio library."
)


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()

    screener = FanOutFanIn(
        agents=[agents["skills"], agents["experience"], agents["collaboration"]],
        aggregator=agents["panel"],
    )

    return BoundedExecution(
        pattern=screener,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Screening error. Return NO HIRE with explanation."),
        max_retries=2,
        timeout_seconds=60.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_screen(safe: BoundedExecution, cv: str):
    return await safe.run(cv)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/cv_screener_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running CV Screen ────────────────────────────────────────────")
    recorder.start("cv_screener")
    result = await run_screen(safe, DEMO_CV)
    print(result.output)

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
