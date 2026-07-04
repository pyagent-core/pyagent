#!/usr/bin/env python3
"""Clinical Summary — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.composite import CompositePattern
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.resolution import SelfReflection
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import MAX_ROUNDS, STOP_PHRASE, build_agents

load_dotenv()
log = logging.getLogger(__name__)

DEMO_NOTE = (
    "68M, CHF exacerbation. Hx: HFrEF (EF 30%), T2DM, CKD3. Allergy: penicillin (rash). "
    "Meds: furosemide 40 mg PO BID, metoprolol succ 50 mg daily. "
    "Vitals: BP 148/92, HR 96, SpO2 91% RA, wt +3 kg from baseline."
)


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()

    extract_and_draft = Pipeline(stages=[agents["extractor"], agents["drafter"]])
    accuracy_pass     = SelfReflection(
        agent=agents["summary_reviewer"],
        max_rounds=MAX_ROUNDS,
        stop_phrase=STOP_PHRASE,
    )
    summarizer = CompositePattern(patterns=[extract_and_draft, accuracy_pass])

    return BoundedExecution(
        pattern=summarizer,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Summarization error. Return raw note extraction only."),
        max_retries=2,
        timeout_seconds=90.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_summary(safe: BoundedExecution, note: str):
    return await safe.run(note)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/clinical_summary_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Clinical Summary ─────────────────────────────────────")
    recorder.start("clinical_summary")
    result = await run_summary(safe, DEMO_NOTE)
    print(result.output)

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
