#!/usr/bin/env python3
"""Code Review System — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.advanced import HumanInTheLoop
from pyagent_patterns.advanced.human_in_the_loop import HumanDecision
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.recovery import BoundedExecution
from pyagent_patterns.resolution import CrossReflection
from pyagent_providers import AnthropicLLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import SECURITY_THRESHOLD, build_agents
from .models import _queue_human_review, parse_security_score

load_dotenv()
log = logging.getLogger(__name__)

DEMO_CODE = """
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
"""


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> tuple[BoundedExecution, HumanInTheLoop]:
    agents = build_agents()

    review = CrossReflection(
        agents=[agents["code_agent"], agents["review_agent"]],
        max_rounds=3,
        stop_phrase="APPROVED",
    )
    security_scan = Pipeline(stages=[agents["security_agent"]])

    def escalation_fn(output: str, metadata: dict) -> HumanDecision:
        score = parse_security_score(output)
        if score >= SECURITY_THRESHOLD:
            return HumanDecision(approved=True, modified_output=output)
        try:
            ticket_id = _queue_human_review(output)
            log.info("Security review queued: ticket=%s", ticket_id)
            return HumanDecision(approved=True,
                                 modified_output=f"[Security Ticket #{ticket_id}]\n{output}")
        except Exception as exc:
            log.warning("Review queue unavailable: %s", exc)
            return HumanDecision(approved=True, modified_output=output)

    hitl = HumanInTheLoop(
        agent=agents["escalation_agent"],
        review_fn=escalation_fn,
        high_risk_keywords=["injection", "XSS", "SSRF", "secret", "hardcoded"],
    )

    safe_review = BoundedExecution(
        pattern=review,
        fallback=Agent("fallback", AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Review error. Return basic code quality assessment."),
        max_retries=2,
        timeout_seconds=120.0,
    )
    return safe_review, hitl, security_scan


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_review(safe: BoundedExecution, code: str):
    return await safe.run(code)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/code_review_demo.jsonl").export_event)

    safe, hitl, security_scan = build(bus, tracker, recorder)

    print("── Running Code Review ──────────────────────────────────────────")
    recorder.start("code_review")
    reviewed = await run_review(safe, DEMO_CODE)
    print(reviewed.output)

    recorder.end(reviewed.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
