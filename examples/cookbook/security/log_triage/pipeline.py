#!/usr/bin/env python3
"""Security Log Triage — orchestration wiring + CLI demo."""
from __future__ import annotations
import asyncio
import logging

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
from .models import _create_soc_case, parse_disposition

load_dotenv()
log = logging.getLogger(__name__)

DEMO_ALERT = (
    '{"rule":"impossible travel","user":"j.doe","from":"US","to":"RU","delta_min":12,'
    '"asset":"vpn-gw-01","mfa":"failed x3"}'
)


def build(bus: TraceEventBus, tracker: CostTracker, recorder: Recorder) -> tuple[BoundedExecution, HumanInTheLoop]:
    agents = build_agents()

    triage = Pipeline(stages=[agents["enricher"], agents["correlator"], agents["classifier"]])

    def page_analyst(output: str, metadata: dict) -> HumanDecision:
        if parse_disposition(output) == "FALSE_POSITIVE":
            return HumanDecision(approved=True, modified_output=f"Auto-closed: {output}")
        try:
            case_id = _create_soc_case(summary=output[:200], metadata=metadata)
            log.info("SOC case created: %s", case_id)
            return HumanDecision(approved=True, modified_output=f"Escalated as case {case_id}\n{output}")
        except Exception as exc:
            log.warning("SOC ticketing unavailable: %s — proceeding", exc)
            return HumanDecision(approved=True, modified_output=output)

    hitl = HumanInTheLoop(
        agent=agents["case_writer"],
        review_fn=page_analyst,
        high_risk_keywords=["ransomware", "exfiltration", "domain admin", "lateral movement"],
    )

    safe = BoundedExecution(
        pattern=triage,
        fallback=Agent("fallback", OpenAILLM("gpt-4o-mini"),
                       system_prompt="Triage error. Flag alert for manual SOC review."),
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
    bus.subscribe(JsonlExporter("traces/log_triage_demo.jsonl").export_event)

    safe, hitl = build(bus, tracker, recorder)

    print("── Running Security Log Triage ──────────────────────────────────")
    recorder.start("log_triage")
    result = await run_triage(safe, DEMO_ALERT)
    print(result.output)

    recorder.end(result.output)
    s = tracker.summary()
    print(f"\n── Cost: ${s['total_cost_usd']:.6f}  By agent: {s['by_agent']} ──")


if __name__ == "__main__":
    asyncio.run(main())
