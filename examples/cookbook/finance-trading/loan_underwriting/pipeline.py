#!/usr/bin/env python3
"""Loan Underwriting Committee — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.resolution import Debate
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import parse_decision

load_dotenv()
log = logging.getLogger(__name__)

DEMO_APPLICATION = (
    "Application: $250k 7-year business loan. DTI 38%, credit score 690, 2 years trading, "
    "revenue $480k (growing), $90k equipment as collateral, one prior late payment."
)


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    committee = Debate(
        debaters=[agents["approve_advocate"], agents["decline_advocate"]],
        judge=agents["senior_underwriter"],
        rounds=2,
    )
    fallback = Agent(
        "fallback", AnthropicLLM("claude-sonnet-4-20250514"),
        system_prompt="Underwriting error. Return REFER for manual review.",
    )
    return BoundedExecution(pattern=committee, fallback=fallback, max_retries=2, timeout_seconds=120.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_committee(safe: BoundedExecution, application: str):
    return await safe.run(application)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/loan_underwriting_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Loan Underwriting Committee ─────────────────────────")
    recorder.start("loan_underwriting")
    result = await run_committee(safe, DEMO_APPLICATION)
    print(result.output)
    print(f"\nDecision: {parse_decision(result.output)}")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
