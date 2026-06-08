"""Run PyAgent benchmarks.

Usage:
    python -m benchmarks.run                     # All suites
    python -m benchmarks.run --suite cost        # Just cost suite
    python -m benchmarks.run --suite quality     # Just quality suite
"""

from __future__ import annotations

import argparse
import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import FanOutFanIn, Pipeline
from pyagent_patterns.resolution import Debate, SelfReflection, Voting

from benchmarks.framework import PatternBenchmark
from benchmarks.suites import COST_SUITE, LATENCY_SUITE, QUALITY_SUITE, ROUTER_SUITE


def build_patterns() -> dict[str, object]:
    """Create patterns with MockLLM for deterministic benchmarking."""

    # Simple pipeline (1 agent)
    simple_llm = MockLLM(responses=[
        "The answer is: Paris is the capital of France. "
        "Renewable energy offers clean solar and wind power, reducing emissions. "
        "def is_palindrome(s): return s == s[::-1]. "
        "Remote work improves flexibility and productivity but challenges communication."
    ])

    # Pipeline (3 stages)
    pipeline_llm = MockLLM(responses=[
        "Extracted facts: capital=Paris, energy=renewable, remote=flexible",
        "Summarized: Paris is the capital. Solar and wind are clean energy. Remote boosts productivity.",
        "Final: Paris. Clean renewable energy from solar/wind. Remote work offers flexibility with communication challenges.",
    ])

    # Self-reflection (2 rounds)
    reflection_llm = MockLLM(responses=[
        "Initial: Paris is the capital. def sort(arr): return sorted(arr). Remote has pros/cons on productivity and communication.",
        "Critique: Missing edge cases for sort. Need more on flexibility and testing confidence in production.",
        "Refined: Paris capital. def sort(arr): if not arr: return []; handles empty, duplicate, negative. Testing catches bugs, builds confidence for production quality.",
        "APPROVED — covers edge cases and key arguments.",
    ])

    # Debate (2 debaters + judge)
    debate_llm = MockLLM(responses=[
        "Pro: Python backend offers clean syntax, strong ecosystem, growth and revenue margin potential.",
        "Con: JavaScript backend with Node.js offers consistency, faster I/O, and user perspective alignment.",
        "Pro rebuttal: Python has better testing frameworks for production quality confidence and bug detection.",
        "Con rebuttal: JavaScript has full-stack flexibility, reducing technical communication overhead.",
        "Judge: Balanced — Python for data/ML backends, JavaScript for real-time. Both support remote productivity.",
    ])

    # Voting (3 voters)
    vote_llms = [
        MockLLM(responses=["Paris. Renewable solar/wind energy is clean. Remote improves flexibility but challenges communication and productivity."]),
        MockLLM(responses=["The capital is Paris. Energy: solar and wind reduce emissions. Remote work: flexibility vs communication tradeoffs in testing."]),
        MockLLM(responses=["Paris. Clean renewable energy from solar/wind. Remote boosts productivity, testing builds confidence for quality production code."]),
    ]

    # Fan-out (3 parallel analysts + aggregator)
    analyst_llms = [
        MockLLM(responses=["Technical: Paris capital, sorting algorithm needs edge cases, TCP reliable vs UDP fast."]),
        MockLLM(responses=["Business: Revenue 10M at 15% growth with 23% margins, renewable energy savings."]),
        MockLLM(responses=["User: Remote flexibility and productivity, communication challenges, testing confidence."]),
    ]
    agg_llm = MockLLM(responses=[
        "Combined: Paris capital. Sort handles empty/duplicate/negative. Revenue $10M 15% growth 23% margin. "
        "Renewable solar/wind clean energy. Remote flexible but communication challenges. TCP reliable, UDP fast."
    ])

    return {
        "single_agent": Pipeline(stages=[Agent("agent", simple_llm)]),
        "pipeline_3stage": Pipeline(stages=[
            Agent("extract", pipeline_llm),
            Agent("summarize", pipeline_llm),
            Agent("format", pipeline_llm),
        ]),
        "self_reflection": SelfReflection(agent=Agent("coder", reflection_llm), max_rounds=2),
        "debate": Debate(
            debaters=[Agent("pro", debate_llm), Agent("con", debate_llm)],
            judge=Agent("judge", debate_llm),
            rounds=2,
        ),
        "voting_3": Voting(voters=[Agent(f"v{i}", llm) for i, llm in enumerate(vote_llms)]),
        "fanout_3": FanOutFanIn(
            agents=[Agent(f"analyst_{i}", llm) for i, llm in enumerate(analyst_llms)],
            aggregator=Agent("agg", agg_llm),
        ),
    }


async def main(suite_name: str | None = None) -> None:
    bench = PatternBenchmark()
    patterns = build_patterns()
    for name, pattern in patterns.items():
        bench.add_pattern(name, pattern)

    suites_map = {
        "cost": COST_SUITE,
        "quality": QUALITY_SUITE,
        "latency": LATENCY_SUITE,
        "router": ROUTER_SUITE,
    }

    suites = [suites_map[suite_name]] if suite_name else list(suites_map.values())

    for suite in suites:
        print(f"\n{'#' * 90}")
        print(f"# Suite: {suite.name}")
        print(f"# {suite.description}")
        print(f"{'#' * 90}")
        results = await bench.run_suite(suite)
        bench.print_report(results)

        stats = bench.compare_patterns(results)
        if len(stats) > 1:
            cheapest = min(stats, key=lambda p: stats[p]["avg_cost_usd"])
            best_quality = max(stats, key=lambda p: stats[p]["avg_quality"])
            fastest = min(stats, key=lambda p: stats[p]["avg_latency_s"])
            print(f"  Cheapest:      {cheapest} (${stats[cheapest]['avg_cost_usd']:.6f}/task)")
            print(f"  Best quality:  {best_quality} ({stats[best_quality]['avg_quality']:.0%})")
            print(f"  Fastest:       {fastest} ({stats[fastest]['avg_latency_s']:.3f}s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run PyAgent benchmarks")
    parser.add_argument("--suite", choices=["cost", "quality", "latency", "router"], default=None)
    args = parser.parse_args()
    asyncio.run(main(args.suite))
