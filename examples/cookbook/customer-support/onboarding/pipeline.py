#!/usr/bin/env python3
"""Customer Onboarding — orchestration wiring + CLI demo."""
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

from .agents import ROUNDS, build_agents

load_dotenv()
log = logging.getLogger(__name__)

DEMO_CUSTOMER = "Acme Corp, 50 seats, Pro plan, contact: alice@acme.com, enterprise SSO required."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    workflow = RoleBased(agents=agents, rounds=ROUNDS)
    return BoundedExecution(
        pattern=workflow,
        fallback=Agent("fallback", OpenAILLM("gpt-4o-mini"),
                       system_prompt="Onboarding error. Send a manual onboarding guide."),
        max_retries=2,
        timeout_seconds=90.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_onboarding(safe: BoundedExecution, info: str):
    return await safe.run(info)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/onboarding_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)
    recorder.start("onboarding")
    result = await run_onboarding(safe, DEMO_CUSTOMER)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
