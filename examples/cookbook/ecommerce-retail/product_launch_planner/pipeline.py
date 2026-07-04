#!/usr/bin/env python3
"""Product Launch Planner — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.orchestration import OrchestratorWorkers
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import build_agents

load_dotenv()
DEMO_BRIEF = "Product: premium wireless keyboard. Target: remote developers. Budget: $129. Launch in 2 weeks."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    planner = OrchestratorWorkers(
        orchestrator=a["launch_lead"],
        workers=[a["pricing"], a["copywriter"], a["seo"], a["inventory"]],
    )
    return BoundedExecution(pattern=planner,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Launch planning error. Return minimal checklist."),
        max_retries=2, timeout_seconds=120.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_plan(safe: BoundedExecution, brief: str): return await safe.run(brief)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/product_launch_planner_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("product_launch_planner")
    result = await run_plan(safe, DEMO_BRIEF)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  Workers: {result.metadata.get('workers_used', [])} ──")

if __name__ == "__main__": asyncio.run(main())
