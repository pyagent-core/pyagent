#!/usr/bin/env python3
"""Regulatory Compliance Checker — orchestration wiring + CLI demo."""
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
log = logging.getLogger(__name__)

DEMO_REGULATION = "GDPR Article 30: Controllers must maintain records of processing activities."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    checker = Hierarchical(
        manager=a["compliance_director"],
        teams=[
            Team(name="Obligations", lead=a["obligations_lead"],
                 workers=[a["requirement_extractor"], a["scope_analyst"]]),
            Team(name="Controls",    lead=a["controls_lead"],
                 workers=[a["policy_mapper"], a["evidence_checker"]]),
        ],
    )
    return BoundedExecution(pattern=checker,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Check error. Flag for manual compliance review."),
        max_retries=2, timeout_seconds=180.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_check(safe: BoundedExecution, doc: str): return await safe.run(doc)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/compliance_checker_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("compliance_checker")
    result = await run_check(safe, DEMO_REGULATION)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")

if __name__ == "__main__": asyncio.run(main())
