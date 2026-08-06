"""BlueprintIR: runtime-independent intermediate representation.

`BlueprintIR` is what every consumer (adapters, differ, renderer, future
Agent Spec exporter) should read from — never the raw Pydantic
`BlueprintSpec` directly. This keeps exactly one place that normalizes the
YAML/Pydantic shape into simple, adapter-friendly data.

`BlueprintSpec` remains the parsing/validation surface (via `pydantic`);
`BlueprintIR` is derived from it via `BlueprintIR.from_spec()` and carries
no pydantic dependency of its own, so downstream consumers (adapters,
tooling) never need to import `pyagent_blueprint.schema`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyagent_blueprint.schema.spec import BlueprintSpec


@dataclass(frozen=True)
class ProviderBindingIR:
    """A named model binding."""

    name: str
    model: str
    provider: str = "mock"
    fallback_ref: str = ""


@dataclass(frozen=True)
class AgentIR:
    """A single agent definition."""

    name: str
    prompt: str
    provider: str = ""
    tools: tuple[str, ...] = ()
    description: str = ""
    guardrails: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecoveryIR:
    """Bounded execution / recovery policy for a workflow."""

    max_retries: int = 2
    timeout_seconds: float = 30.0
    fallback_provider: str = ""


@dataclass(frozen=True)
class WorkflowIR:
    """A named workflow: pattern + agent wiring + recovery/guardrails."""

    name: str
    pattern: str
    agents: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    recovery: RecoveryIR | None = None
    guardrails: tuple[str, ...] = ()


@dataclass(frozen=True)
class SLAIR:
    """Service-level constraints for a workflow's contract."""

    latency_p95_ms: float = 5000.0
    cost_max_usd: float = 0.10
    quality_min: float = 0.0


@dataclass(frozen=True)
class ContractIR:
    """Input/output contract + SLA for a workflow (maps to Agent Spec
    Component Inputs/Outputs where JSON-Schema-shaped; SLA has no Agent
    Spec equivalent — see diagnostics.SLA_UNSUPPORTED)."""

    workflow: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    sla: SLAIR = field(default_factory=SLAIR)


@dataclass(frozen=True)
class MemoryPolicyIR:
    """Memory-tier configuration (maps to nothing in Agent Spec today —
    see diagnostics.MEMORY_TIER_UNSUPPORTED)."""

    working_max_tokens: int = 50_000
    session_backend: str = "json"
    semantic_enabled: bool = False
    compression_policy: str = "none"
    compression_target_ratio: float = 0.5
    redaction_max_sensitivity: str | None = None


@dataclass(frozen=True)
class ObservabilityIR:
    """Tracing + cost budget configuration."""

    tracing_enabled: bool = True
    tracing_exporter: str = "console"
    cost_budget_daily_usd: float | None = None
    cost_budget_alert_threshold: float = 0.8


@dataclass(frozen=True)
class BlueprintIR:
    """Root intermediate representation of a complete blueprint.

    This is the single normalized structure that `RuntimeAdapter.compile()`,
    `BlueprintDiffer`, `BlueprintRenderer`, and any future exporter (e.g. an
    Agent Spec backend) should consume — never the raw `BlueprintSpec`.
    """

    api_version: str
    name: str
    version: str
    description: str = ""
    tags: tuple[str, ...] = ()
    owner: str = ""
    providers: dict[str, ProviderBindingIR] = field(default_factory=dict)
    agents: dict[str, AgentIR] = field(default_factory=dict)
    workflows: dict[str, WorkflowIR] = field(default_factory=dict)
    contracts: dict[str, ContractIR] = field(default_factory=dict)
    memory: MemoryPolicyIR | None = None
    observability: ObservabilityIR | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_spec(cls, spec: BlueprintSpec) -> BlueprintIR:
        """Build a `BlueprintIR` from a validated `BlueprintSpec`.

        This is the ONE place that knows how to read the Pydantic schema.
        Everything downstream (adapters, differ, renderer) should be
        written against this dataclass shape instead.
        """
        providers = {
            name: ProviderBindingIR(
                name=name,
                model=binding.model,
                provider=binding.provider,
                fallback_ref=binding.fallback_ref,
            )
            for name, binding in spec.providers.items()
        }

        agents = {
            name: AgentIR(
                name=name,
                prompt=agent_spec.prompt,
                provider=agent_spec.provider,
                tools=tuple(agent_spec.tools),
                description=agent_spec.description,
                guardrails=tuple(agent_spec.guardrails),
            )
            for name, agent_spec in spec.agents.items()
        }

        workflows = {
            name: WorkflowIR(
                name=name,
                pattern=wf.pattern,
                agents=dict(wf.agents),
                config=dict(wf.config),
                recovery=(
                    RecoveryIR(
                        max_retries=wf.recovery.max_retries,
                        timeout_seconds=wf.recovery.timeout_seconds,
                        fallback_provider=wf.recovery.fallback_provider,
                    )
                    if wf.recovery is not None
                    else None
                ),
                guardrails=tuple(wf.guardrails),
            )
            for name, wf in spec.workflows.items()
        }

        contracts = {
            name: ContractIR(
                workflow=name,
                input_schema=dict(contract.input),
                output_schema=dict(contract.output),
                sla=SLAIR(
                    latency_p95_ms=contract.sla.latency_p95_ms,
                    cost_max_usd=contract.sla.cost_max_usd,
                    quality_min=contract.sla.quality_min,
                ),
            )
            for name, contract in spec.contracts.items()
        }

        memory = None
        if spec.context is not None:
            redaction = spec.context.redaction
            memory = MemoryPolicyIR(
                working_max_tokens=spec.context.memory.working_max_tokens,
                session_backend=spec.context.memory.session_backend,
                semantic_enabled=spec.context.memory.semantic_enabled,
                compression_policy=spec.context.compression.policy,
                compression_target_ratio=spec.context.compression.target_ratio,
                redaction_max_sensitivity=(redaction.max_sensitivity if redaction else None),
            )

        observability = None
        if spec.observability is not None:
            budget = spec.observability.cost_budget
            observability = ObservabilityIR(
                tracing_enabled=spec.observability.tracing.enabled,
                tracing_exporter=spec.observability.tracing.exporter,
                cost_budget_daily_usd=(budget.daily_usd if budget else None),
                cost_budget_alert_threshold=(budget.alert_threshold if budget else 0.8),
            )

        return cls(
            api_version=spec.api_version,
            name=spec.metadata.name,
            version=spec.metadata.version,
            description=spec.metadata.description,
            tags=tuple(spec.metadata.tags),
            owner=spec.metadata.owner,
            providers=providers,
            agents=agents,
            workflows=workflows,
            contracts=contracts,
            memory=memory,
            observability=observability,
            extensions={},
        )

    def governance_features(self) -> dict[str, bool]:
        """Which governance features this blueprint actually declares.

        Used by adapters/conformance checks to know what MUST be honored
        or diagnosed — never silently dropped. Keys map 1:1 to the
        diagnostic codes in `diagnostics.py`.
        """
        return {
            "routing": any(p.fallback_ref for p in self.providers.values()),
            "budget": any(c.sla.cost_max_usd for c in self.contracts.values())
            or (self.observability is not None and self.observability.cost_budget_daily_usd is not None),
            "sla": bool(self.contracts),
            "memory_tier": self.memory is not None,
            "recovery": any(w.recovery is not None for w in self.workflows.values()),
            "guardrails": any(a.guardrails for a in self.agents.values())
            or any(w.guardrails for w in self.workflows.values()),
            "checkpoint": any(w.config.get("human_in_the_loop") for w in self.workflows.values()),
        }
