"""Example: Full-stack — Router + Compression + Guardrails + Pattern + Tracing."""

import asyncio

from pyagent_compress import MessageCompressor, TokenBudget
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.guardrails import GuardrailChain, LengthGuard, PIIGuard
from pyagent_patterns.orchestration import Supervisor
from pyagent_patterns.recovery import BoundedExecution
from pyagent_router import ModelSelector
from pyagent_trace import CostTracker


async def main():
    # 1. Guardrails: sanitize input
    guardrails = GuardrailChain([PIIGuard(redact=True), LengthGuard(max_chars=5000)])
    user_input = "My email is user@test.com. I need a refund for order #123."
    check = guardrails.check(user_input)
    safe_input = check.sanitized_content or user_input
    print(f"1. Guardrails: {safe_input}")

    # 2. Router: select model
    selector = ModelSelector()
    selection = selector.select(safe_input)
    print(f"2. Router: {selection.model} (difficulty {selection.difficulty.score}/10)")

    # 3. Pattern: Supervisor with routes
    supervisor = Supervisor(
        classifier=Agent("classifier", MockLLM(responses=["billing"])),
        routes={
            "billing": Agent("billing", MockLLM(responses=["Refund of $50 processed for order #123."])),
            "tech": Agent("tech", MockLLM(responses=["Try restarting your device."])),
        },
    )

    # 4. Recovery: bounded execution
    bounded = BoundedExecution(pattern=supervisor, timeout_seconds=10.0)
    result = await bounded.run(safe_input)
    print(f"3. Pattern: {result.output}")

    # 5. Compression: compress output for downstream
    compressor = MessageCompressor(target_ratio=0.7)
    compressed = compressor.compress(result.output)
    print(f"4. Compression: {compressed.savings_pct:.0%} saved")

    # 6. Cost tracking
    tracker = CostTracker()
    tracker.record("supervisor", "classifier", selection.model, 50, 20, selection.cost_estimate.total_cost)
    tracker.record("supervisor", "billing", selection.model, 100, 50, selection.cost_estimate.total_cost * 2)
    print(f"5. Cost: ${tracker.total_cost:.6f}")
    print(f"   By agent: {tracker.by_agent()}")

    # 7. Token budget
    budget = TokenBudget(workflow_limit=10_000)
    budget.consume("classifier", 70)
    budget.consume("billing", 150)
    print(f"6. Budget: {budget.remaining()} tokens remaining ({budget.workflow_utilization:.1%} used)")

if __name__ == "__main__":
    asyncio.run(main())
