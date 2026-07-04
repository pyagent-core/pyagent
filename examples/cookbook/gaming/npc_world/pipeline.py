#!/usr/bin/env python3
"""Emergent NPC World — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.structural import Blackboard
from pyagent_patterns.structural.blackboard import BlackboardAgent
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import OpenAILLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import build_agents

load_dotenv()
DEMO_SCENARIO = "Initial state: unexplored forest world. Resources: 10 wood, 5 stone. Population: 3."
ROUNDS = 3


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    world = Blackboard(
        agents=[
            BlackboardAgent(agent=a["explorer"],   reads=["world_map"],                     writes=["world_map", "resources"]),
            BlackboardAgent(agent=a["builder"],     reads=["world_map", "resources"],        writes=["world_map", "resources"]),
            BlackboardAgent(agent=a["trader"],      reads=["resources", "world_map"],        writes=["economy"]),
            BlackboardAgent(agent=a["chronicler"],  reads=["world_map", "resources", "economy"], writes=["chronicle"]),
        ],
        rounds=ROUNDS,
    )
    return BoundedExecution(pattern=world,
        fallback=Agent("fallback", OpenAILLM("gpt-4o-mini"),
                       system_prompt="Simulation error. Return minimal world state."),
        max_retries=2, timeout_seconds=120.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_world(safe: BoundedExecution, scenario: str): return await safe.run(scenario)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/npc_world_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("npc_world")
    result = await run_world(safe, DEMO_SCENARIO)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f} ──")

if __name__ == "__main__": asyncio.run(main())
