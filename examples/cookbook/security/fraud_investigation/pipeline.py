#!/usr/bin/env python3
"""Fraud Investigation — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.advanced import ReAct
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import OpenAILLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import MAX_STEPS, TOOLS, build_agents

load_dotenv()
log = logging.getLogger(__name__)

DEMO_ALERT = "Alert: account ACC-8842 triggered a velocity rule. Investigate and recommend an action."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()

    investigator = ReAct(
        agent=agents["fraud_analyst"],
        tools=TOOLS,
        max_steps=MAX_STEPS,
    )

    return BoundedExecution(
        pattern=investigator,
        fallback=Agent("fallback", OpenAILLM("gpt-4o-mini"),
                       system_prompt="Investigation error. Flag alert for manual review."),
        max_retries=2,
        timeout_seconds=120.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_investigation(safe: BoundedExecution, alert: str):
    return await safe.run(alert)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/fraud_investigation_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Fraud Investigation ──────────────────────────────────")
    recorder.start("fraud_investigation")
    result = await run_investigation(safe, DEMO_ALERT)
    print(result.output)
    print(f"\nSteps: {result.metadata.get('steps', '?')}  Tools: {result.metadata.get('tools_used', [])}")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
