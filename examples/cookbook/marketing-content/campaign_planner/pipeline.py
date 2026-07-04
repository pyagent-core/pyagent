#!/usr/bin/env python3
"""Marketing Campaign Planner — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.parallelism import FanOutFanIn
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import build_agents

load_dotenv()
DEMO_BRIEF = "Product: AI-powered CRM tool. Target: SMB sales teams. Goal: 500 signups in 30 days. Budget: $20k."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    planner = FanOutFanIn(
        workers=[a["email_specialist"], a["social_specialist"], a["blog_specialist"]],
        aggregator=a["campaign_director"],
    )
    return BoundedExecution(pattern=planner,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Campaign error. Return minimal 3-channel plan."),
        max_retries=2, timeout_seconds=120.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_campaign(safe: BoundedExecution, brief: str): return await safe.run(brief)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/campaign_planner_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("campaign_planner")
    result = await run_campaign(safe, DEMO_BRIEF)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  Workers used: {result.metadata.get('workers_used', [])} ──")

if __name__ == "__main__": asyncio.run(main())
