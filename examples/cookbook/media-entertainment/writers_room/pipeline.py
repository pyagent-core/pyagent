#!/usr/bin/env python3
"""Writers' Room — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.coordination import RoleBased
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import ROUNDS, build_agents

load_dotenv()
DEMO_PITCH = "Episode concept: The heist of a century interrupted by a power outage. Genre: thriller."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    room = RoleBased(agents=agents, rounds=ROUNDS)
    return BoundedExecution(pattern=room,
        fallback=Agent("fallback", AnthropicLLM("claude-haiku-4-5"),
                       system_prompt="Writers' room error. Return a minimal scene outline."),
        max_retries=2, timeout_seconds=180.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_room(safe: BoundedExecution, pitch: str): return await safe.run(pitch)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/writers_room_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("writers_room")
    result = await run_room(safe, DEMO_PITCH)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  Rounds: {ROUNDS} ──")

if __name__ == "__main__": asyncio.run(main())
