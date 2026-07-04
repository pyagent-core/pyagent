#!/usr/bin/env python3
"""AML Monitoring — orchestration wiring + CLI demo.

Run:
    python -m examples.cookbook.finance-trading.aml_monitoring.pipeline
"""
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
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

from .agents import build_agents
from .models import parse_tier

load_dotenv()
log = logging.getLogger(__name__)


# ── HTTP integration stubs ───────────────────────────────────────────────────

async def _post_case(summary: str, account_id: str) -> str:
    """Submit case to compliance review queue; return ticket_id."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            os.environ["COMPLIANCE_API_URL"] + "/cases",
            json={"account_id": account_id, "summary": summary[:500], "source": "aml-agent"},
            headers={"Authorization": f"Bearer {os.environ['COMPLIANCE_API_KEY']}"},
        )
        r.raise_for_status()
        return r.json()["ticket_id"]


async def _poll_decision(ticket_id: str, timeout_s: float = 300.0) -> bool:
    """Poll until an officer approves or rejects. Returns True = approved."""
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        deadline = asyncio.get_event_loop().time() + timeout_s
        while asyncio.get_event_loop().time() < deadline:
            r = await client.get(
                f"{os.environ['COMPLIANCE_API_URL']}/cases/{ticket_id}",
                headers={"Authorization": f"Bearer {os.environ['COMPLIANCE_API_KEY']}"},
            )
            data = r.json()
            if data["status"] in ("approved", "rejected"):
                log.info("Compliance %s: %s", ticket_id, data["status"])
                return data["status"] == "approved"
            await asyncio.sleep(5.0)
    log.warning("Compliance decision timed out for %s — defaulting reject", ticket_id)
    return False


# ── Build ─────────────────────────────────────────────────────────────────────

def build(
    bus: TraceEventBus,
    tracker: CostTracker,
    recorder: Recorder,
    account_id: str = "unknown",
) -> tuple[BoundedExecution, HumanInTheLoop]:
    agents = build_agents()

    triage = Pipeline(stages=[
        agents["rule_screener"],
        agents["risk_scorer"],
        agents["enrichment"],
    ])

    def review_fn(output: str, metadata: dict) -> HumanDecision:
        tier = parse_tier(output)
        if tier != "High":
            return HumanDecision(approved=True, modified_output=output)
        loop = asyncio.get_event_loop()
        ticket_id = loop.run_until_complete(_post_case(output, account_id))
        approved  = loop.run_until_complete(_poll_decision(ticket_id))
        return HumanDecision(approved=approved, modified_output=output)

    sar_writer = HumanInTheLoop(
        agent=agents["sar_drafter"],
        review_fn=review_fn,
        high_risk_keywords=["High", "sanctions", "structuring"],
    )
    safe_triage = BoundedExecution(
        pattern=triage,
        fallback=build_agents()["rule_screener"].__class__(
            "fallback", OpenAILLM("gpt-4o-mini"),
            system_prompt="Triage error. Log alert for manual compliance review.",
        ),
        max_retries=2,
        timeout_seconds=45.0,
    )
    return safe_triage, sar_writer


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def run_triage(pipeline: BoundedExecution, alert: str):
    return await pipeline.run(alert)


# ── CLI demo ──────────────────────────────────────────────────────────────────

DEMO_ALERT = (
    "Transaction: $9,850 wire from ACC-7731 (US) to ACME Consulting Ltd (Cyprus). "
    "Third such transfer in 48h. Counterparty newly registered; no prior relationship."
)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    bus      = TraceEventBus()
    tracker  = CostTracker(event_bus=bus)
    recorder = Recorder(event_bus=bus)
    bus.subscribe(ConsoleExporter().export_event)
    bus.subscribe(JsonlExporter("traces/aml_demo.jsonl").export_event)

    safe_triage, sar_writer = build(bus, tracker, recorder, account_id="ACC-7731")

    print("── Running AML triage ──────────────────────────────────────────")
    recorder.start("aml_pipeline")
    result = await run_triage(safe_triage, DEMO_ALERT)
    print(result.output)

    tier = parse_tier(result.output)
    if tier == "High":
        print("\n── High-risk: routing to SAR drafter ──────────────────────")
        sar = await sar_writer.run(result.output)
        print(sar.output)

    recorder.end(result.output)

    print("\n── Cost summary ────────────────────────────────────────────────")
    s = tracker.summary()
    print(f"  Total  : ${s['total_cost_usd']:.6f}")
    print(f"  Tokens : {s['total_tokens']}")
    print(f"  By agent: {s['by_agent']}")
    print(f"  By model: {s['by_model']}")

    print("\n── Agent communication trace ───────────────────────────────────")
    for e in recorder.llm_calls:
        snippet = e.response[:70].replace("\n", " ")
        print(f"  {e.agent_name:20s}  {snippet}…")

    print(f"\n── Trace → traces/aml_demo.jsonl  ({len(recorder.entries)} events) ──")


if __name__ == "__main__":
    asyncio.run(main())
