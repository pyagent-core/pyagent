#!/usr/bin/env python3
"""Essay Grader — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.resolution import Voting
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import OpenAILLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import RUBRIC, build_agents

load_dotenv()
DEMO_ESSAY = "Title: Why Cities Should Invest in Public Transit\n\nPublic transit reduces traffic, cuts emissions, and connects communities..."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    grader = Voting(
        voters=[a["grader_openai"], a["grader_anthropic"], a["grader_gemini"]],
        strategy="majority",
    )
    return BoundedExecution(pattern=grader,
        fallback=Agent("fallback", OpenAILLM("gpt-4o-mini"),
                       system_prompt=RUBRIC),
        max_retries=2, timeout_seconds=90.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_grade(safe: BoundedExecution, essay: str): return await safe.run(essay)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/essay_grader_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("essay_grader")
    result = await run_grade(safe, DEMO_ESSAY)
    print(result.output)
    print(f"\nTally: {result.metadata.get('tally', {})}")
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f} ──")

if __name__ == "__main__": asyncio.run(main())
