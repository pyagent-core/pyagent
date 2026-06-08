"""Example: Recovery — bounded execution and circuit breaker."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.recovery import BoundedExecution, CircuitBreaker


async def main():
    # Bounded execution with fallback
    primary = Pipeline(stages=[Agent("expensive", MockLLM(responses=["Premium result"]))])
    fallback = Pipeline(stages=[Agent("cheap", MockLLM(responses=["Budget result"]))])

    bounded = BoundedExecution(
        pattern=primary,
        fallback=fallback,
        max_retries=2,
        timeout_seconds=10.0,
    )
    result = await bounded.run("Analyze market trends")
    print(f"Output: {result.output}")
    print(f"Recovery level: {result.metadata.get('recovery_level', 'N/A')}")

    # Circuit breaker
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=1.0)
    print(f"\nCircuit state: {cb.state.value}")

    # Simulate failures
    cb._on_failure()
    print(f"After 1 failure: {cb.state.value}")
    cb._on_failure()
    print(f"After 2 failures: {cb.state.value} (opens!)")

    # Recovery
    cb._on_success()
    print(f"After success: {cb.state.value}")


if __name__ == "__main__":
    asyncio.run(main())
