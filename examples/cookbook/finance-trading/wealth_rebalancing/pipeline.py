#!/usr/bin/env python3
"""Wealth Rebalancing Crew — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import OpenAILLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import is_compliant

load_dotenv()
log = logging.getLogger(__name__)

DEMO_INPUT = """
Client: ACC-1188 — age 52, retirement in 8 years. Risk: Moderate.
Constraints: no fossil fuels, max 5% single name, min 10% bonds.
Current holdings: AAPL 18%, MSFT 12%, SPY 20%, AGG 15%, cash 35%.
"""


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    pipeline = Pipeline(stages=[
        agents["risk_profiler"],
        agents["market_scanner"],
        agents["allocation_strategist"],
        agents["compliance_checker"],
    ])
    fallback = build_agents()["risk_profiler"].__class__(
        "fallback", OpenAILLM("gpt-4o-mini"),
        system_prompt="Rebalancing error. Return current holdings unchanged.",
    )
    return BoundedExecution(pattern=pipeline, fallback=fallback, max_retries=2, timeout_seconds=60.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_rebalance(safe_pipeline: BoundedExecution, brief: str):
    return await safe_pipeline.run(brief)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/wealth_rebalancing_demo.jsonl").export_event)

    safe_pipeline = build(bus, tracker, recorder)

    print("── Running Wealth Rebalancing Crew ─────────────────────────────")
    recorder.start("rebalance")
    result = await run_rebalance(safe_pipeline, DEMO_INPUT)
    print(result.output)
    print(f"\nCompliant: {is_compliant(result.output)}")

    recorder.end(result.output)
    print("\n── Cost summary ────────────────────────────────────────────────")
    s = tracker.summary()
    print(f"  Total  : ${s['total_cost_usd']:.6f}")
    print(f"  By agent: {s['by_agent']}")
    for e in recorder.llm_calls:
        print(f"  {e.agent_name:25s}  {e.response[:60].replace(chr(10),' ')}…")


if __name__ == "__main__":
    asyncio.run(main())
