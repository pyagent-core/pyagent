#!/usr/bin/env python3
"""Research Assistant — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.advanced import ReAct
from pyagent_patterns.composite import CompositePattern
from pyagent_patterns.orchestration import FanOutFanIn, Pipeline
from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.resolution import Debate
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import (ACADEMIC_TOOLS, INDUSTRY_TOOLS, WEB_TOOLS, build_agents)

load_dotenv()
log = logging.getLogger(__name__)

DEMO_QUESTION = "What is the current state of LLM reasoning capabilities and key open challenges?"


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()

    web_react      = ReAct(agent=agents["web_agent"],      tools=WEB_TOOLS,      max_steps=4)
    academic_react = ReAct(agent=agents["academic_agent"], tools=ACADEMIC_TOOLS, max_steps=4)
    industry_react = ReAct(agent=agents["industry_agent"], tools=INDUSTRY_TOOLS, max_steps=3)

    gather = FanOutFanIn(
        agents=[web_react, academic_react, industry_react],
        aggregator=agents["judge"],
    )
    debate_step = Debate(
        debaters=[agents["optimist"], agents["sceptic"]],
        judge=agents["judge"],
        rounds=2,
    )
    synthesize = Pipeline(stages=[agents["synthesizer"]])

    full_pipeline = CompositePattern(patterns=[gather, debate_step, synthesize])

    return BoundedExecution(
        pattern=full_pipeline,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Research error. Return a concise summary of what is known."),
        max_retries=2,
        timeout_seconds=180.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_research(safe: BoundedExecution, question: str):
    return await safe.run(question)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/research_assistant_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Research Assistant ───────────────────────────────────")
    recorder.start("research_assistant")
    result = await run_research(safe, DEMO_QUESTION)
    print(result.output)

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
