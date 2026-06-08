"""Benchmark framework: measure cost, latency, quality, and token usage across patterns.

Usage:
    python -m benchmarks.run          # Run all benchmarks
    python -m benchmarks.run --suite cost  # Cost-effectiveness only
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from pyagent_patterns.base import Pattern, Result


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    pattern_name: str
    task: str
    output: str
    duration_seconds: float
    token_estimate: int
    cost_estimate_usd: float
    metadata: dict[str, Any] = field(default_factory=dict)
    quality_score: float | None = None


@dataclass
class BenchmarkSuite:
    """A collection of benchmark tasks with expected outputs."""

    name: str
    tasks: list[BenchmarkTask]
    description: str = ""


@dataclass
class BenchmarkTask:
    """A single benchmark task."""

    name: str
    prompt: str
    expected_keywords: list[str] = field(default_factory=list)
    max_cost_usd: float = 0.10
    max_latency_seconds: float = 60.0


class PatternBenchmark:
    """Run benchmarks across patterns and collect comparative results.

    Usage:
        bench = PatternBenchmark()
        bench.add_pattern("pipeline", pipeline_instance)
        bench.add_pattern("reflection", reflection_instance)
        results = await bench.run_suite(cost_suite)
        bench.print_report(results)
    """

    def __init__(self) -> None:
        self._patterns: dict[str, Pattern] = {}
        self._cost_per_token: float = 0.000002  # Default: ~gpt-4o-mini rate

    def add_pattern(self, name: str, pattern: Pattern) -> None:
        """Register a pattern for benchmarking."""
        self._patterns[name] = pattern

    def set_cost_rate(self, cost_per_token: float) -> None:
        """Set the cost-per-token rate for estimates."""
        self._cost_per_token = cost_per_token

    async def run_task(self, pattern_name: str, task: BenchmarkTask) -> BenchmarkResult:
        """Run a single task against a single pattern."""
        pattern = self._patterns[pattern_name]
        start = time.perf_counter()
        result = await pattern.run(task.prompt)
        elapsed = time.perf_counter() - start

        cost = result.token_estimate * self._cost_per_token

        quality = None
        if task.expected_keywords:
            output_lower = result.output.lower()
            matches = sum(1 for kw in task.expected_keywords if kw.lower() in output_lower)
            quality = matches / len(task.expected_keywords)

        return BenchmarkResult(
            pattern_name=pattern_name,
            task=task.name,
            output=result.output,
            duration_seconds=elapsed,
            token_estimate=result.token_estimate,
            cost_estimate_usd=cost,
            metadata=result.metadata,
            quality_score=quality,
        )

    async def run_suite(self, suite: BenchmarkSuite) -> list[BenchmarkResult]:
        """Run all tasks in a suite against all registered patterns."""
        results: list[BenchmarkResult] = []
        for pattern_name in self._patterns:
            for task in suite.tasks:
                try:
                    r = await self.run_task(pattern_name, task)
                    results.append(r)
                except Exception as e:
                    results.append(BenchmarkResult(
                        pattern_name=pattern_name,
                        task=task.name,
                        output=f"ERROR: {e}",
                        duration_seconds=0.0,
                        token_estimate=0,
                        cost_estimate_usd=0.0,
                        metadata={"error": str(e)},
                    ))
        return results

    @staticmethod
    def print_report(results: list[BenchmarkResult]) -> None:
        """Print a formatted benchmark report."""
        print("\n" + "=" * 90)
        print(f"{'Pattern':<25} {'Task':<20} {'Latency':>10} {'Tokens':>8} {'Cost':>10} {'Quality':>8}")
        print("-" * 90)
        for r in results:
            q = f"{r.quality_score:.0%}" if r.quality_score is not None else "N/A"
            print(
                f"{r.pattern_name:<25} {r.task:<20} "
                f"{r.duration_seconds:>9.3f}s {r.token_estimate:>8} "
                f"${r.cost_estimate_usd:>9.6f} {q:>8}"
            )
        print("=" * 90)

        # Aggregated by pattern
        patterns = sorted(set(r.pattern_name for r in results))
        print(f"\n{'Pattern':<25} {'Avg Latency':>12} {'Avg Tokens':>12} {'Avg Cost':>12} {'Avg Quality':>12}")
        print("-" * 75)
        for p in patterns:
            pr = [r for r in results if r.pattern_name == p]
            avg_lat = sum(r.duration_seconds for r in pr) / len(pr)
            avg_tok = sum(r.token_estimate for r in pr) / len(pr)
            avg_cost = sum(r.cost_estimate_usd for r in pr) / len(pr)
            quality_results = [r for r in pr if r.quality_score is not None]
            avg_q = sum(r.quality_score for r in quality_results) / len(quality_results) if quality_results else 0
            print(
                f"{p:<25} {avg_lat:>11.3f}s {avg_tok:>12.0f} "
                f"${avg_cost:>11.6f} {avg_q:>11.0%}"
            )
        print()

    @staticmethod
    def compare_patterns(results: list[BenchmarkResult]) -> dict[str, dict[str, float]]:
        """Return per-pattern aggregate stats as a dict."""
        patterns = sorted(set(r.pattern_name for r in results))
        out: dict[str, dict[str, float]] = {}
        for p in patterns:
            pr = [r for r in results if r.pattern_name == p]
            quality_results = [r for r in pr if r.quality_score is not None]
            out[p] = {
                "avg_latency_s": sum(r.duration_seconds for r in pr) / len(pr),
                "avg_tokens": sum(r.token_estimate for r in pr) / len(pr),
                "avg_cost_usd": sum(r.cost_estimate_usd for r in pr) / len(pr),
                "avg_quality": (
                    sum(r.quality_score for r in quality_results) / len(quality_results)
                    if quality_results else 0.0
                ),
            }
        return out
