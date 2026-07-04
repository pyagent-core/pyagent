#!/usr/bin/env python3
"""SQL Analytics Assistant — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.advanced import ReAct
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import MAX_STEPS, TOOLS, build_agents

load_dotenv()
DEMO_QUESTION = "Which three regions had the highest revenue last quarter?"


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    analyst = ReAct(agent=a["sql_analyst"], tools=TOOLS, max_steps=MAX_STEPS)
    return BoundedExecution(pattern=analyst,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="SQL error. Return canned top-3 regions."),
        max_retries=2, timeout_seconds=90.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_query(safe: BoundedExecution, question: str): return await safe.run(question)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/sql_analyst_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("sql_analyst")
    result = await run_query(safe, DEMO_QUESTION)
    print(result.output)
    print(f"\nSteps: {result.metadata.get('steps', '?')}  Tools: {result.metadata.get('tools_used', [])}")
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f} ──")

if __name__ == "__main__": asyncio.run(main())
