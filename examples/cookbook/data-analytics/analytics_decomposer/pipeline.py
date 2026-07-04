#!/usr/bin/env python3
"""Analytics Decomposer — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

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
log = logging.getLogger(__name__)

DEMO_QUESTION = "Why did customer churn rise in Q3? Break it down by plan tier and tenure."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()

    analytics = OrchestratorWorkers(
        orchestrator=agents["analytics_lead"],
        workers=[agents["query"], agents["transform"], agents["chart"]],
    )

    return BoundedExecution(
        pattern=analytics,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Analytics error. Return a simplified analysis."),
        max_retries=2,
        timeout_seconds=90.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_analytics(safe: BoundedExecution, question: str):
    return await safe.run(question)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/analytics_decomposer_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Analytics Decomposer ─────────────────────────────────")
    recorder.start("analytics_decomposer")
    result = await run_analytics(safe, DEMO_QUESTION)
    print(result.output)
    print(f"\nWorkers used: {result.metadata.get('workers_used', [])}")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
