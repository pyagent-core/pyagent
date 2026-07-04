#!/usr/bin/env python3
"""Robo-Advisor Onboarding — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.structural import RoleBased
from pyagent_providers import OpenAILLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import is_suitable

load_dotenv()
log = logging.getLogger(__name__)

DEMO_ANSWERS = """
I'm 34 years old, software engineer earning $145k/year. I have $280k to invest
and want to retire comfortably at 60. I can tolerate some volatility — I lost money
in 2022 and stayed invested. I won't need this money for at least 10 years.
"""


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    onboarding = RoleBased(agents=agents, rounds=1)
    fallback = Agent(
        "fallback", OpenAILLM("gpt-4o-mini"),
        system_prompt="Onboarding error. Apologize and ask client to retry.",
    )
    return BoundedExecution(pattern=onboarding, fallback=fallback, max_retries=2, timeout_seconds=90.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_onboarding(safe: BoundedExecution, answers: str):
    return await safe.run(answers)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/robo_advisor_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Robo-Advisor Onboarding ─────────────────────────────")
    recorder.start("robo_advisor")
    result = await run_onboarding(safe, DEMO_ANSWERS)
    print(result.output)
    print(f"\nRoles: {result.metadata.get('agent_names')}  Suitable: {is_suitable(result.output)}")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
