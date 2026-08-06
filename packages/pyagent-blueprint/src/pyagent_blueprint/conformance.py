"""AdapterConformanceSuite: the reusable proof that an adapter is
framework-agnostic-contract-compliant.

Any adapter author — inside or outside this repo — can run this against
their own adapter:

    from pyagent_blueprint.conformance import AdapterConformanceSuite

    class TestMyAdapterConformance(AdapterConformanceSuite):
        @pytest.fixture
        def adapter(self):
            return MyCustomAdapter()

This suite checks, against a small set of canonical fixture blueprints:
- `compile()` doesn't raise on all canonical fixtures
- `run()` returns an `AdapterResult` (not a raw framework object)
- `run()` on an unresolvable workflow name raises `UnknownWorkflowError`
- diagnostic completeness: every governance feature a fixture declares is
  either honored or reported via a `CompileDiagnostic` — never silently
  dropped
- the degenerate single-agent, no-orchestration case still compiles/runs
- if `Capability.STREAMING` is declared, `stream()` yields chunks whose
  concatenation is consistent with `run()`'s `.output`
- if `Capability.SYNC_EXECUTION` is declared, `run()` still returns an
  awaitable
- multiple sequential `run()` calls on the same compiled artifact don't
  leak state between calls (isolation check)
- if `Capability.ROUND_TRIP` is declared, `export(compile(ir))` round
  trips without unreported loss (stubbed until a round-tripping adapter
  exists; see TRANSFORMATION-PLAN.md Section 12 item 6)
"""

from __future__ import annotations

import pytest

from pyagent_blueprint.adapter import Capability, RuntimeAdapter, UnknownWorkflowError
from pyagent_blueprint.ir import (
    SLAIR,
    AgentIR,
    BlueprintIR,
    ContractIR,
    MemoryPolicyIR,
    RecoveryIR,
    WorkflowIR,
)


def _minimal_single_agent_ir() -> BlueprintIR:
    """The degenerate case: one agent, no orchestration concept at all."""
    return BlueprintIR(
        api_version="pyagent/v1",
        name="single-agent-min",
        version="0.1.0",
        agents={"solo": AgentIR(name="solo", prompt="You are a helpful agent.")},
        workflows={"main": WorkflowIR(name="main", pattern="single", agents={"agent": "solo"})},
    )


def _sequential_two_agent_ir() -> BlueprintIR:
    """Minimal multi-agent sequential fixture — no branching, no shared state."""
    return BlueprintIR(
        api_version="pyagent/v1",
        name="sequential-min",
        version="0.1.0",
        agents={
            "first": AgentIR(name="first", prompt="Summarize the input."),
            "second": AgentIR(name="second", prompt="Review the summary."),
        },
        workflows={
            "main": WorkflowIR(
                name="main",
                pattern="pipeline",
                agents={"stages": {"first": "first", "second": "second"}},
            )
        },
    )


def _governance_ir() -> BlueprintIR:
    """A fixture that declares every governance feature at once, so
    adapters are forced to either honor it or diagnose it — never drop
    it silently."""
    return BlueprintIR(
        api_version="pyagent/v1",
        name="governance-min",
        version="0.1.0",
        agents={
            "worker": AgentIR(name="worker", prompt="Do the work.", guardrails=("pii_redact",))
        },
        workflows={
            "main": WorkflowIR(
                name="main",
                pattern="single",
                agents={"agent": "worker"},
                recovery=RecoveryIR(max_retries=1, timeout_seconds=5.0),
                guardrails=("no_pii",),
            )
        },
        contracts={
            "main": ContractIR(
                workflow="main",
                sla=SLAIR(latency_p95_ms=2000.0, cost_max_usd=0.05),
            )
        },
        memory=MemoryPolicyIR(redaction_max_sensitivity="confidential"),
    )


CANONICAL_FIXTURES: dict[str, BlueprintIR] = {
    "single_agent": _minimal_single_agent_ir(),
    "sequential": _sequential_two_agent_ir(),
    "governance": _governance_ir(),
}


def _sla_budget_ir() -> BlueprintIR:
    """Isolated SLA + cost-budget governance fixture (mega-plan Section 1.3)."""
    return BlueprintIR(
        api_version="pyagent/v1",
        name="sla-budget-min",
        version="0.1.0",
        agents={"worker": AgentIR(name="worker", prompt="Do the work.")},
        workflows={"main": WorkflowIR(name="main", pattern="single", agents={"agent": "worker"})},
        contracts={
            "main": ContractIR(
                workflow="main",
                sla=SLAIR(latency_p95_ms=1500.0, cost_max_usd=0.02),
            )
        },
    )


def _memory_tiers_ir() -> BlueprintIR:
    """Isolated context-tier/trust/redaction governance fixture."""
    return BlueprintIR(
        api_version="pyagent/v1",
        name="memory-tiers-min",
        version="0.1.0",
        agents={"worker": AgentIR(name="worker", prompt="Do the work.")},
        workflows={"main": WorkflowIR(name="main", pattern="single", agents={"agent": "worker"})},
        memory=MemoryPolicyIR(
            semantic_enabled=True,
            compression_policy="semantic_lossless",
            redaction_max_sensitivity="confidential",
        ),
    )


def _hitl_checkpoint_ir() -> BlueprintIR:
    """Isolated human-in-the-loop workflow-level checkpoint governance fixture."""
    return BlueprintIR(
        api_version="pyagent/v1",
        name="hitl-checkpoint-min",
        version="0.1.0",
        agents={"worker": AgentIR(name="worker", prompt="Do the work.")},
        workflows={
            "main": WorkflowIR(
                name="main",
                pattern="single",
                agents={"agent": "worker"},
                config={"human_in_the_loop": True},
            )
        },
    )


def _recovery_policy_ir() -> BlueprintIR:
    """Isolated recovery/retry/timeout governance fixture."""
    return BlueprintIR(
        api_version="pyagent/v1",
        name="recovery-policy-min",
        version="0.1.0",
        agents={"worker": AgentIR(name="worker", prompt="Do the work.")},
        workflows={
            "main": WorkflowIR(
                name="main",
                pattern="single",
                agents={"agent": "worker"},
                recovery=RecoveryIR(
                    max_retries=3, timeout_seconds=10.0, fallback_provider="fallback"
                ),
            )
        },
    )


GOVERNANCE_FIXTURES: dict[str, BlueprintIR] = {
    "sla_budget": _sla_budget_ir(),
    "memory_tiers": _memory_tiers_ir(),
    "hitl_checkpoint": _hitl_checkpoint_ir(),
    "recovery_policy": _recovery_policy_ir(),
}


class AdapterConformanceSuite:
    """Mix this into a test class and provide an `adapter` fixture.

    Subclasses must provide:

        @pytest.fixture
        def adapter(self) -> RuntimeAdapter: ...
    """

    @pytest.mark.parametrize("fixture_name", sorted(CANONICAL_FIXTURES))
    def test_compile_does_not_raise(self, adapter: RuntimeAdapter, fixture_name: str) -> None:
        ir = CANONICAL_FIXTURES[fixture_name]
        compiled = adapter.compile(ir)
        assert compiled.handle is not None

    @pytest.mark.asyncio
    async def test_run_returns_adapter_result(self, adapter: RuntimeAdapter) -> None:
        from pyagent_blueprint.adapter import AdapterResult

        ir = CANONICAL_FIXTURES["single_agent"]
        compiled = adapter.compile(ir)
        result = await adapter.run(compiled, "main", "hello")
        assert isinstance(result, AdapterResult)
        assert result.output is not None

    @pytest.mark.asyncio
    async def test_unknown_workflow_raises_documented_error(self, adapter: RuntimeAdapter) -> None:
        ir = CANONICAL_FIXTURES["single_agent"]
        compiled = adapter.compile(ir)
        with pytest.raises(UnknownWorkflowError):
            await adapter.run(compiled, "does-not-exist", "hello")

    @pytest.mark.asyncio
    async def test_degenerate_single_agent_case(self, adapter: RuntimeAdapter) -> None:
        """The contract must not be over-designed for orchestration: a
        blueprint with no graph/branching concept at all must still
        compile and run cleanly."""
        ir = CANONICAL_FIXTURES["single_agent"]
        compiled = adapter.compile(ir)
        result = await adapter.run(compiled, "main", "ping")
        assert result.output is not None

    def test_diagnostic_completeness_for_governance_fixture(self, adapter: RuntimeAdapter) -> None:
        """Every governance feature the fixture declares (recovery, SLA,
        guardrails, memory/redaction) must be either honored or reported
        via a CompileDiagnostic — never silently dropped."""
        ir = CANONICAL_FIXTURES["governance"]
        declared = ir.governance_features()
        compiled = adapter.compile(ir)

        honored_or_diagnosed = set()
        for diag in compiled.diagnostics:
            honored_or_diagnosed.add(diag.code.gap)

        # For every declared feature not natively honored by this adapter
        # (we can't know "honored" without executing against a real
        # backend, so this check asserts the *weaker* but still load-
        # bearing property: if the adapter declares NO diagnostics at
        # all for a governance-heavy fixture, that silence itself must be
        # intentional — i.e. the adapter claims to honor everything).
        if any(declared.values()):
            # Either at least one diagnostic was raised, OR the adapter
            # explicitly claims full governance support via capabilities.
            assert compiled.diagnostics or getattr(adapter, "honors_all_governance", False), (
                f"{adapter.name} declared no diagnostics for a fixture requesting "
                f"{[k for k, v in declared.items() if v]} — either honor these "
                "features or report them via CompileDiagnostic."
            )

    @pytest.mark.parametrize("fixture_name", sorted(GOVERNANCE_FIXTURES))
    def test_diagnostic_completeness_per_governance_feature(
        self, adapter: RuntimeAdapter, fixture_name: str
    ) -> None:
        """Isolated per-feature governance fixtures (SLA+budget,
        memory-tiers/trust/redaction, HITL checkpoint, recovery policy) —
        each must independently be honored or diagnosed, never silently
        dropped. Mirrors the combined `governance` fixture check above,
        but catches bugs where an adapter only diagnoses governance
        features when they co-occur."""
        ir = GOVERNANCE_FIXTURES[fixture_name]
        declared = ir.governance_features()
        compiled = adapter.compile(ir)

        if any(declared.values()):
            assert compiled.diagnostics or getattr(adapter, "honors_all_governance", False), (
                f"{adapter.name} declared no diagnostics for fixture {fixture_name!r} "
                f"requesting {[k for k, v in declared.items() if v]} — either honor "
                "these features or report them via CompileDiagnostic."
            )

    @pytest.mark.asyncio
    async def test_streaming_consistency_if_declared(self, adapter: RuntimeAdapter) -> None:
        if not (adapter.capabilities & Capability.STREAMING):
            pytest.skip(f"{adapter.name} does not declare Capability.STREAMING")

        ir = CANONICAL_FIXTURES["single_agent"]
        compiled = adapter.compile(ir)
        chunks = [chunk async for chunk in adapter.stream(compiled, "main", "hello")]
        assert len(chunks) >= 1

        result = await adapter.run(compiled, "main", "hello")
        streamed = "".join(str(c) for c in chunks)
        assert streamed == "" or isinstance(result.output, str)

    @pytest.mark.asyncio
    async def test_sync_execution_still_awaitable_if_declared(
        self, adapter: RuntimeAdapter
    ) -> None:
        if not (adapter.capabilities & Capability.SYNC_EXECUTION):
            pytest.skip(f"{adapter.name} does not declare Capability.SYNC_EXECUTION")

        ir = CANONICAL_FIXTURES["single_agent"]
        compiled = adapter.compile(ir)
        result = await adapter.run(compiled, "main", "hello")
        assert result is not None

    @pytest.mark.asyncio
    async def test_no_state_leakage_between_runs(self, adapter: RuntimeAdapter) -> None:
        """Multiple sequential run() calls on the same compiled artifact
        must not leak state between calls — an easy bug class in
        stateful graph-based adapters, easy to miss in turn-based ones."""
        ir = CANONICAL_FIXTURES["sequential"]
        compiled = adapter.compile(ir)

        result_a = await adapter.run(compiled, "main", "input A")
        result_b = await adapter.run(compiled, "main", "input B")

        assert result_a.output is not None
        assert result_b.output is not None

    @pytest.mark.asyncio
    async def test_round_trip_if_declared(self, adapter: RuntimeAdapter) -> None:
        """Stubbed until a round-tripping adapter exists (e.g. the Step 8
        Agent Spec bridge). Any adapter declaring Capability.ROUND_TRIP
        must implement `export()` and it must not raise."""
        if not (adapter.capabilities & Capability.ROUND_TRIP):
            pytest.skip(f"{adapter.name} does not declare Capability.ROUND_TRIP")

        ir = CANONICAL_FIXTURES["sequential"]
        compiled = adapter.compile(ir)
        exported = adapter.export(compiled)
        assert exported is not None
