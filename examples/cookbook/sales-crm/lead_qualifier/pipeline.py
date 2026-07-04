#!/usr/bin/env python3
"""Lead Qualifier — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.orchestration import Supervisor
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import build_agents
from .models import parse_tier

load_dotenv()
DEMO_LEAD = "Company: TechCorp (500 employees). Budget: $50k/yr. Need: CRM upgrade by Q3. Decision maker: VP Sales."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    a = build_agents()
    router = Supervisor(
        supervisor=a["lead_scorer"],
        workers={
            "hot":  Pipeline(stages=[a["account_exec"]]),
            "warm": Pipeline(stages=[a["nurture_specialist"]]),
            "cold": Pipeline(stages=[a["cold_hold"]]),
        },
        route_fn=lambda output, _meta: parse_tier(output),
    )
    return BoundedExecution(pattern=router,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Lead qualification error. Tag lead as warm and assign to nurture."),
        max_retries=2, timeout_seconds=90.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_qualify(safe: BoundedExecution, lead: str): return await safe.run(lead)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/lead_qualifier_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("lead_qualifier")
    result = await run_qualify(safe, DEMO_LEAD)
    print(result.output)
    print(f"\nTier: {result.metadata.get('route', '?')}  Worker: {result.metadata.get('worker_used', '?')}")
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f} ──")

if __name__ == "__main__": asyncio.run(main())
