#!/usr/bin/env python3
"""Portfolio Review — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.orchestration import Supervisor
from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.resolution import EvaluatorOptimizer
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import MEMO_CRITERIA, build_agents
from .models import parse_score

load_dotenv()
log = logging.getLogger(__name__)

DEMO_HOLDING = "Apple Inc. (AAPL), 8% of portfolio, long equity, $142.50, PE 28×."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()

    desk = Supervisor(
        classifier=agents["router"],
        routes={
            "equity":       agents["equities"],
            "fixed_income": agents["rates"],
            "risk":         agents["risk"],
        },
        default_route="risk",
    )
    memo = EvaluatorOptimizer(
        generator=agents["writer"],
        evaluator=agents["reviewer"],
        criteria=MEMO_CRITERIA,
        quality_threshold=8,
        max_rounds=3,
    )

    async def full_review(holding: str):
        analysis = await desk.run(holding)
        return await memo.run(analysis.output)

    class _FullReview:
        async def run(self, holding: str):
            return await full_review(holding)

    return BoundedExecution(
        pattern=_FullReview(),
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Review error. Return minimal holding analysis."),
        max_retries=2,
        timeout_seconds=120.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_review(safe: BoundedExecution, holding: str):
    return await safe.run(holding)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/portfolio_review_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Portfolio Review ─────────────────────────────────────")
    recorder.start("portfolio_review")
    result = await run_review(safe, DEMO_HOLDING)
    print(result.output)
    print(f"\nMemo quality score: {parse_score(result.output)}/10")

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
