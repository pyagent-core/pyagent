#!/usr/bin/env python3
"""Trading Signal Desk — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import AnthropicLLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import parse_conviction, parse_direction

load_dotenv()
log = logging.getLogger(__name__)

DEMO_MARKET_DATA = """
Ticker: ACME Corp (ACM)
Price: $142.50  |  1-week change: +8.3%
MA20: $135  MA50: $128  MA200: $115  (price above all MAs)
RSI(14): 71  |  Bollinger: price at upper band
Volume: 2× average over 5 days
Put/Call ratio: 0.55 (bullish skew)  |  VIX: 18 (calm)
News: beat Q2 earnings by 12%; analyst upgrades ×3 this week
"""


def build(
    bus: TraceEventBus,
    tracker: CostTracker,
    recorder: Recorder,
) -> BoundedExecution:
    agents = build_agents()

    desk = FanOutFanIn(
        agents=[agents["momentum"], agents["mean_reversion"], agents["sentiment"]],
        aggregator=agents["signal_aggregator"],
    )
    return BoundedExecution(
        pattern=desk,
        fallback=agents["signal_aggregator"].__class__(
            "fallback", AnthropicLLM("claude-sonnet-4-20250514"),
            system_prompt="Signal generation error. Return FLAT conviction 1.",
        ),
        max_retries=2,
        timeout_seconds=60.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_signal(desk: BoundedExecution, market_data: str):
    return await desk.run(market_data)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/trading_signals_demo.jsonl").export_event)

    desk = build(bus, tracker, recorder)

    print("── Running Trading Signal Desk ─────────────────────────────────")
    recorder.start("trading_signals")
    result = await run_signal(desk, DEMO_MARKET_DATA)
    print(result.output)

    direction  = parse_direction(result.output)
    conviction = parse_conviction(result.output)
    print(f"\nParsed: direction={direction}  conviction={conviction}/10")

    recorder.end(result.output)

    print("\n── Cost summary ────────────────────────────────────────────────")
    s = tracker.summary()
    print(f"  Total  : ${s['total_cost_usd']:.6f}")
    print(f"  Tokens : {s['total_tokens']}")
    print(f"  By agent: {s['by_agent']}")

    print("\n── Agent communication trace ───────────────────────────────────")
    for e in recorder.llm_calls:
        print(f"  {e.agent_name:20s}  {e.response[:70].replace(chr(10), ' ')}…")

    print(f"\n── Trace → traces/trading_signals_demo.jsonl  ({len(recorder.entries)} events) ──")


if __name__ == "__main__":
    asyncio.run(main())
