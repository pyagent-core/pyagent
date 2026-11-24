"""Orchestration pipeline demonstrating guarded execution with DnsMiddleware."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from pyagent_dns.blueprint import load_blueprint_dns
from pyagent_dns.middleware import DnsMiddleware
from pyagent_patterns.advanced.react import ReAct
from pyagent_patterns.base import LLMCallable, MockLLM

from .agents import build_analyst_agent, build_tools

RECIPE_DIR = Path(__file__).resolve().parent


def build_guarded_system(
    llm: LLMCallable | None = None,
    event_bus: Any = None,
) -> tuple[DnsMiddleware, ReAct]:
    """Assemble the DNS middleware, tools, and guarded ReAct agent."""
    bundle = load_blueprint_dns(RECIPE_DIR / "blueprint.yaml")
    middleware = DnsMiddleware(bundle.resolver, bundle.graph, event_bus=event_bus)

    raw_tools = build_tools()
    guarded_tools = middleware.guard_tools(
        raw_tools,
        principal_chain=["portfolio_analyst"],
        purpose="portfolio_audit",
    )

    if llm is None:
        llm = MockLLM(
            responses=[
                "Thought: I need positions.\nAction: portfolio-data.reader(ACC-101)\n",
                "Thought: Got positions.\nFINISH: Portfolio has AAPL and MSFT.",
            ]
        )

    agent = build_analyst_agent(llm)
    pattern = ReAct(agent=agent, tools=guarded_tools, max_steps=4)
    return middleware, pattern


async def run_pipeline(task: str, llm: LLMCallable | None = None) -> dict[str, Any]:
    """Execute the guarded pipeline and measure latency."""
    start_time = time.perf_counter()
    middleware, pattern = build_guarded_system(llm=llm)

    result = await pattern.run(task)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return {
        "output": result.output,
        "decisions": [
            {
                "capability": d.capability,
                "allowed": d.allowed,
                "reason_code": d.reason_code,
                "obligations": [ob.value for ob in d.obligations],
            }
            for d in middleware.decisions
        ],
        "latency_ms": elapsed_ms,
    }


def main() -> None:
    """CLI entrypoint."""
    res = asyncio.run(run_pipeline("Audit portfolio positions for customer ACC-101"))
    print(f"Pipeline finished in {res['latency_ms']:.2f}ms")
    print(f"Output: {res['output']}")
    print(f"Decisions: {res['decisions']}")


if __name__ == "__main__":
    main()
