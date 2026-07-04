#!/usr/bin/env python3
"""ESG Report Analyzer — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.orchestration import OrchestratorWorkers
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import parse_rating

load_dotenv()
log = logging.getLogger(__name__)

DEMO_INPUT = """
Company: ACME Industrial Corp
Mandate: SFDR Article 8, exclude weapons and coal, EU taxonomy alignment required.
Annual Report Excerpt: Scope 1: 450k tCO2e, Scope 2: 180k tCO2e, Scope 3: undisclosed.
Net-zero target: 2040. Board: 28% women. Recent controversy: supplier labor audit (2023).
MSCI rating: BBB. Sustainalytics: 34 (medium). ISS: C+.
"""


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    esg = OrchestratorWorkers(
        orchestrator=agents["esg_lead"],
        workers=[agents["ratings"], agents["disclosure_extractor"],
                 agents["sfdr_scorer"], agents["controversy"]],
    )
    fallback = agents["esg_lead"].__class__(
        "fallback", AnthropicLLM("claude-sonnet-4-20250514"),
        system_prompt="ESG analysis error. Return C rating with no analysis.",
    )
    return BoundedExecution(pattern=esg, fallback=fallback, max_retries=2, timeout_seconds=90.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_esg(safe: BoundedExecution, brief: str):
    return await safe.run(brief)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/esg_analyzer_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running ESG Report Analyzer ─────────────────────────────────")
    recorder.start("esg_analysis")
    result = await run_esg(safe, DEMO_INPUT)
    print(result.output)
    print(f"\nParsed ESG Rating: {parse_rating(result.output)}")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
