#!/usr/bin/env python3
"""Incident Triage Pipeline — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging
import os

import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from pyagent_patterns.advanced import HumanInTheLoop
from pyagent_patterns.advanced.human_in_the_loop import HumanDecision
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.recovery import BoundedExecution
from pyagent_providers import OpenAILLM
from pyagent_patterns.base import Agent
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import parse_touches_prod

load_dotenv()
log = logging.getLogger(__name__)

DEMO_INCIDENT = (
    "ALERT: checkout 5xx rate 12% for 8 min. Logs: 'connection pool exhausted' on payments-svc; "
    "db connections pinned at 100/100; deploy of payments-svc 14 min ago."
)


async def _page_on_call_and_wait(summary: str, timeout_s: float = 300.0) -> bool:
    routing_key = os.environ["PAGERDUTY_ROUTING_KEY"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://events.pagerduty.com/v2/enqueue",
            json={
                "routing_key": routing_key,
                "event_action": "trigger",
                "payload": {"summary": summary[:200], "severity": "critical", "source": "pyagent"},
            },
        )
        r.raise_for_status()
        dedup_key = r.json()["dedup_key"]

        deadline = asyncio.get_event_loop().time() + timeout_s
        while asyncio.get_event_loop().time() < deadline:
            resp = await client.get(
                f"https://api.pagerduty.com/incidents?incident_key={dedup_key}",
                headers={"Authorization": f"Token token={os.environ['PAGERDUTY_API_KEY']}"},
            )
            incidents = resp.json().get("incidents", [])
            if incidents and incidents[0].get("status") == "acknowledged":
                return True
            await asyncio.sleep(5.0)
    return False


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> tuple[BoundedExecution, HumanInTheLoop]:
    agents = build_agents()

    triage = Pipeline(stages=[
        agents["log_analyst"],
        agents["root_cause"],
        agents["remediation"],
    ])

    def on_call_gate(output: str, metadata: dict) -> HumanDecision:
        if not parse_touches_prod(output):
            return HumanDecision(approved=True, modified_output=f"Auto-applied (non-prod):\n{output}")
        approved = asyncio.get_event_loop().run_until_complete(_page_on_call_and_wait(output))
        return HumanDecision(
            approved=approved,
            modified_output=output if approved else "REJECTED by on-call — escalate to IC.",
        )

    hitl = HumanInTheLoop(
        agent=agents["runbook_writer"],
        review_fn=on_call_gate,
        high_risk_keywords=["delete", "drop", "scale to zero", "failover", "restart prod"],
    )

    safe = BoundedExecution(
        pattern=triage,
        fallback=Agent("fallback", OpenAILLM("gpt-4o-mini"),
                       system_prompt="Triage error. Log alert for manual review."),
        max_retries=2,
        timeout_seconds=90.0,
    )
    return safe, hitl


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_triage(safe: BoundedExecution, alert: str):
    return await safe.run(alert)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/incident_triage_demo.jsonl").export_event)

    safe, hitl = build(bus, tracker, recorder)

    print("── Running Incident Triage ──────────────────────────────────────")
    recorder.start("incident_triage")
    triaged = await run_triage(safe, DEMO_INCIDENT)
    print(triaged.output)

    recorder.end(triaged.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
