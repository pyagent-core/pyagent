#!/usr/bin/env python3
"""Earnings Call Analyzer — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.resolution import SelfReflection
from pyagent_providers import AnthropicLLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import STOP_PHRASE, build_agents
from .models import is_complete

load_dotenv()
log = logging.getLogger(__name__)

DEMO_TRANSCRIPT = """
[Q2 Earnings Call — ACME Corp]
CEO: "We delivered another strong quarter. Revenue came in at $1.24B, up 14% year-over-year."
CFO: "EPS was $1.82, consensus was $1.68. Free cash flow was $310M.
      Full-year revenue range tightened to $4.9–5.0B from $4.7–5.1B, raising the midpoint."
Analyst Q: "Can you comment on capex plans for H2?"
CFO: "We will continue to invest prudently. I don't want to get into specific numbers today."
"""


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    analyzer = SelfReflection(
        agent=agents["earnings_analyst"],
        max_rounds=3,
        stop_phrase=STOP_PHRASE,
    )
    fallback = agents["earnings_analyst"].__class__(
        "fallback", AnthropicLLM("claude-sonnet-4-20250514"),
        system_prompt="Earnings analysis error. Return incomplete analysis.",
    )
    return BoundedExecution(pattern=analyzer, fallback=fallback, max_retries=2, timeout_seconds=120.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_analysis(safe: BoundedExecution, transcript: str):
    return await safe.run(transcript)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/earnings_call_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Earnings Call Analyzer ──────────────────────────────")
    recorder.start("earnings_call")
    result = await run_analysis(safe, DEMO_TRANSCRIPT)
    print(result.output)
    print(f"\nRounds: {result.metadata.get('rounds', '?')}  Complete: {is_complete(result.output)}")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  Tokens: {s['total_tokens']} ──")


if __name__ == "__main__":
    asyncio.run(main())
