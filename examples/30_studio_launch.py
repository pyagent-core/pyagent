"""Example 30: Launch PyAgent Studio TUI.

Demonstrates:
- Headless service usage (no TUI required)
- BlueprintService for load/validate/compile
- SimulationService for running with MockLLM
- GovernanceService for compliance scoring

To launch the full TUI:
    pip install pyagent-studio[tui]
    pyagent-studio blueprint.yaml
"""

import asyncio

from pyagent_studio import (
    BlueprintService,
    GovernanceService,
    SimulationService,
)


async def main() -> None:
    # Load blueprint via service
    svc = BlueprintService()
    spec = svc.load("packages/pyagent-blueprint/tests/fixtures/customer_support.yaml")
    print(f"Loaded: {svc.summary()}")

    # Validate
    issues = svc.validate()
    print(f"Validation: {len(issues)} issue(s)")

    # Compile
    graph = svc.compile()
    print(f"Compiled: {graph.describe()}")

    # Simulate
    sim = SimulationService()
    result = await sim.run(spec, "support", "I can't see my invoice")
    print(f"\nSimulation: {'✓' if result.success else '✗'}")
    print(f"  Output: {result.output[:100]}")
    print(f"  Elapsed: {result.elapsed_ms:.0f}ms")

    # Governance
    gov = GovernanceService()
    report = gov.check_compliance(spec)
    print(f"\n{gov.format_report(report)}")


if __name__ == "__main__":
    asyncio.run(main())
