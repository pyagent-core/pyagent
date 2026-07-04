#!/usr/bin/env python3
"""Startup Simulation — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.structural import RoleBased
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import ROUNDS, build_agents

load_dotenv()
log = logging.getLogger(__name__)

DEMO_IDEA = "Idea: a CLI that summarizes a git repo's recent activity into a weekly stand-up note."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()

    company = RoleBased(agents=agents, rounds=ROUNDS)

    return BoundedExecution(
        pattern=company,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Simulation error. Return a minimal PRD for the idea."),
        max_retries=2,
        timeout_seconds=180.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_simulation(safe: BoundedExecution, idea: str):
    return await safe.run(idea)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/startup_simulation_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Startup Simulation ───────────────────────────────────")
    recorder.start("startup_simulation")
    result = await run_simulation(safe, DEMO_IDEA)
    print(result.output)
    print(f"\nRoles: {result.metadata.get('roles', [])}  Rounds: {result.metadata.get('rounds', ROUNDS)}")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
