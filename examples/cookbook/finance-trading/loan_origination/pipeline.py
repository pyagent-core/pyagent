#!/usr/bin/env python3
"""Loan Origination Workflow — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.structural import Topology, TopologyType
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import is_complete, parse_decision

load_dotenv()
log = logging.getLogger(__name__)

DEMO_APPLICATION = """
Applicant: Jane Smith, age 42. Loan: $180k mortgage, 25yr term.
Income: $95k/year (W2 + 1099, 3yr self-employment). DTI stated: 32%.
Documents provided: tax returns (2yr), bank statements (3mo), pay stubs (2mo).
Missing: employer verification letter.
Credit score: 740. No late payments in 5yr. Prior mortgage paid off.
"""


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    origination = Topology(agents=agents, topology=TopologyType.CHAIN)
    fallback = Agent(
        "fallback", AnthropicLLM("claude-sonnet-4-20250514"),
        system_prompt="Origination error. Return REFER for manual review.",
    )
    return BoundedExecution(pattern=origination, fallback=fallback, max_retries=2, timeout_seconds=90.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_origination(safe: BoundedExecution, application: str):
    return await safe.run(application)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/loan_origination_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Loan Origination Workflow ───────────────────────────")
    recorder.start("loan_origination")
    result = await run_origination(safe, DEMO_APPLICATION)
    print(result.output)
    print(f"\nDecision: {parse_decision(result.output)}  Complete: {is_complete(result.output)}")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
