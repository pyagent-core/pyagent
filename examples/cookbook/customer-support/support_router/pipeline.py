#!/usr/bin/env python3
"""Customer Support Router — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.advanced import HumanInTheLoop
from pyagent_patterns.advanced.human_in_the_loop import HumanDecision
from pyagent_patterns.orchestration import Supervisor
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import OpenAILLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import parse_intent, _create_zendesk_ticket

load_dotenv()
log = logging.getLogger(__name__)

DEMO_QUERY = "I was charged twice for my annual subscription last month."


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> BoundedExecution:
    agents = build_agents()

    def escalation_fn(output: str, metadata: dict) -> HumanDecision:
        try:
            ticket_id = _create_zendesk_ticket(output, "high")
            log.info("Zendesk ticket created: %s", ticket_id)
            return HumanDecision(approved=True,
                                 modified_output=f"[Ticket #{ticket_id}]\n{output}")
        except Exception as exc:
            log.warning("Zendesk unavailable: %s — auto-approving for fallback", exc)
            return HumanDecision(approved=True, modified_output=output)

    human_gate = HumanInTheLoop(
        agent=agents["escalation"],
        review_fn=escalation_fn,
        high_risk_keywords=["urgent", "legal", "chargeback", "refund"],
    )

    router = Supervisor(
        classifier=agents["supervisor"],
        routes={
            "billing":   agents["billing"],
            "technical": agents["technical"],
            "account":   agents["account"],
            "escalate":  human_gate,
        },
        default_route="escalate",
    )

    return BoundedExecution(
        pattern=router,
        fallback=Agent("fallback", OpenAILLM("gpt-4o-mini"),
                       system_prompt="Support routing error. Apologize and offer to connect with a human."),
        max_retries=2,
        timeout_seconds=60.0,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_support(safe: BoundedExecution, query: str):
    return await safe.run(query)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/support_router_demo.jsonl").export_event)

    safe = build(bus, tracker, recorder)

    print("── Running Support Router ───────────────────────────────────────")
    recorder.start("support_router")
    result = await run_support(safe, DEMO_QUERY)
    print(result.output)

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
