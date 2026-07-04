#!/usr/bin/env python3
"""Trip-Planning Swarm — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.coordination import Swarm
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import GeminiLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import build_agents

load_dotenv()
DEMO_TRIP = "10-day trip to Japan in April. Two adults, budget $6,000 total. Interests: food, temples, hiking. Flying from SFO."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    swarm = Swarm(agents=agents)
    return BoundedExecution(pattern=swarm,
        fallback=Agent("fallback", GeminiLLM("gemini-2.0-flash"),
                       system_prompt="Trip planning error. Return basic Japan itinerary template."),
        max_retries=2, timeout_seconds=180.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_trip(safe: BoundedExecution, request: str): return await safe.run(request)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/trip_planner_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("trip_planner")
    result = await run_trip(safe, DEMO_TRIP)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  Agents in swarm: {result.metadata.get('agents_used', [])} ──")

if __name__ == "__main__": asyncio.run(main())
