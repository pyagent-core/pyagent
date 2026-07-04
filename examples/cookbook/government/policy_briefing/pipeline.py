#!/usr/bin/env python3
"""Policy Briefing Pipeline — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.orchestration import Hierarchical
from pyagent_patterns.orchestration.hierarchical import Team
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import build_agents

load_dotenv()
DEMO_TOPIC = "Proposed carbon tax legislation at $50/tonne — assess economic impact and legal viability."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    pipeline = Hierarchical(
        manager=a["policy_director"],
        teams=[
            Team(name="Economics", lead=a["economics_lead"],
                 workers=[a["macro_analyst"], a["impact_modeler"]]),
            Team(name="Legal",     lead=a["legal_lead"],
                 workers=[a["constitutional_analyst"], a["precedent_researcher"]]),
        ],
    )
    return BoundedExecution(pattern=pipeline,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Briefing error. Return high-level policy summary."),
        max_retries=2, timeout_seconds=180.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_brief(safe: BoundedExecution, topic: str): return await safe.run(topic)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/policy_briefing_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("policy_briefing")
    result = await run_brief(safe, DEMO_TOPIC)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")

if __name__ == "__main__": asyncio.run(main())
