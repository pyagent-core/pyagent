#!/usr/bin/env python3
"""Property Valuation Stack — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.structural import Layered
from pyagent_patterns.structural.layered import Layer
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import build_agents

load_dotenv()
DEMO_PROPERTY = "3BR/2BA single-family home, 1,850 sqft, built 1998. Location: Austin TX 78704. Last sold $420k in 2021."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    stack = Layered(layers=[
        Layer(name="gather",   agents=[a["data_gatherer"], a["comparables_finder"]]),
        Layer(name="analyze",  agents=[a["market_analyst"]]),
        Layer(name="narrate",  agents=[a["narrative_writer"]]),
        Layer(name="qa",       agents=[a["qa_reviewer"]]),
    ])
    return BoundedExecution(pattern=stack,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Valuation error. Return estimated range based on address only."),
        max_retries=2, timeout_seconds=150.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_valuation(safe: BoundedExecution, property_desc: str): return await safe.run(property_desc)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/property_valuation_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("property_valuation")
    result = await run_valuation(safe, DEMO_PROPERTY)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")

if __name__ == "__main__": asyncio.run(main())
