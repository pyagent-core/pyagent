#!/usr/bin/env python3
"""Peer-Review Mesh — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio, logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pyagent_patterns.structural import Topology
from pyagent_patterns.structural.topology import TopologyType
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from .agents import TOPOLOGY_TYPE, build_agents

load_dotenv()
DEMO_ABSTRACT = "Title: LLM Scaling Laws Revisited. Abstract: We demonstrate compute-optimal training beyond Chinchilla predictions, achieving 15% lower perplexity at same compute budget using novel data mixing..."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()
    mesh = Topology(agents=agents, topology=TOPOLOGY_TYPE)
    return BoundedExecution(pattern=mesh,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Review error. Return generic acceptance recommendation."),
        max_retries=2, timeout_seconds=180.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_review(safe: BoundedExecution, paper: str): return await safe.run(paper)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/peer_review_demo.jsonl").export_event)
    safe = build(bus, tracker, recorder)
    recorder.start("peer_review")
    result = await run_review(safe, DEMO_ABSTRACT)
    print(result.output)
    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  Topology: MESH ──")

if __name__ == "__main__": asyncio.run(main())
