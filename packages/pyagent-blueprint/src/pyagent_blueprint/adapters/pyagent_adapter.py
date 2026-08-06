"""PyAgentAdapter: RuntimeAdapter implementation for our own native
runtime (`pyagent-patterns`).

Extracted from `compiler.py` per TRANSFORMATION-PLAN.md Step 3. This is
the baseline reference adapter — it proves the `RuntimeAdapter` contract
works for the runtime it was extracted from before any other adapter is
built or judged against it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pyagent_patterns.base import Agent, MockLLM

from pyagent_blueprint.adapter import (
    AdapterResult,
    Capability,
    CompiledArtifact,
    CompileDiagnostic,
    RuntimeAdapter,
    UnknownWorkflowError,
)
from pyagent_blueprint.diagnostics import (
    BUDGET_UNSUPPORTED,
    CHECKPOINT_UNSUPPORTED,
    GUARDRAIL_UNSUPPORTED,
    MEMORY_TIER_UNSUPPORTED,
    RECOVERY_UNSUPPORTED,
    ROUTING_UNSUPPORTED,
    SLA_UNSUPPORTED,
)
from pyagent_blueprint.runtime import RuntimeGraph

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pyagent_blueprint.ir import BlueprintIR

logger = logging.getLogger(__name__)

# Keys that only exist as governance signals for `_diagnose_ungoverned_features`
# (reported via CompileDiagnostic) — never native pattern-constructor kwargs.
_GOVERNANCE_ONLY_CONFIG_KEYS = frozenset({"human_in_the_loop", "checkpoint"})


class PyAgentCompilationError(Exception):
    """Raised when a BlueprintIR cannot be compiled to a RuntimeGraph."""


class PyAgentAdapter(RuntimeAdapter):
    """Compiles a `BlueprintIR` into a `pyagent-patterns` `RuntimeGraph`.

    Structural shape: composed `Pattern` objects, our own DAG-like
    abstraction — the baseline every other adapter is stress-tested
    against for structural dissimilarity (see TRANSFORMATION-PLAN.md
    Section 6).
    """

    name = "pyagent"
    # Native runtime honors recovery (via RuntimeGraph hooks the caller
    # wires manually) and reports, rather than silently drops, the
    # governance features it does NOT auto-enforce at compile time.
    capabilities = Capability.PARTIAL_WORKFLOW_RUN

    def __init__(self, provider_registry: Any = None) -> None:
        self._provider_registry = provider_registry

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics: list[CompileDiagnostic] = []
        intent: dict[str, str] = {}

        llm_map = self._resolve_providers(ir, diagnostics)
        agent_map = self._build_agents(ir, llm_map)
        workflows = self._build_workflows(ir, agent_map, diagnostics, intent)

        self._diagnose_ungoverned_features(ir, diagnostics)

        graph = RuntimeGraph(
            workflows=workflows,
            agents=agent_map,
            metadata={"name": ir.name, "version": ir.version, "description": ir.description},
        )
        return CompiledArtifact(handle=graph, diagnostics=diagnostics, intent=intent)

    async def run(
        self, compiled: CompiledArtifact, workflow: str, input_: str, **kwargs: Any
    ) -> AdapterResult:
        graph: RuntimeGraph = compiled.handle
        if workflow not in graph:
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow}'. Available: {graph.workflow_names}"
            )
        result = await graph.run(workflow, input_)
        return AdapterResult(output=result.output, raw=result)

    async def stream(
        self, compiled: CompiledArtifact, workflow: str, input_: str, **kwargs: Any
    ) -> AsyncIterator[Any]:
        graph: RuntimeGraph = compiled.handle
        if workflow not in graph:
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow}'. Available: {graph.workflow_names}"
            )
        async for chunk in graph.stream(workflow, input_):
            yield chunk

    def supported_patterns(self) -> list[str]:
        from pyagent_patterns.registry import list_patterns

        return list(list_patterns())

    # -- internals, ported from compiler.py, operating on BlueprintIR --

    def _resolve_providers(
        self, ir: BlueprintIR, diagnostics: list[CompileDiagnostic]
    ) -> dict[str, Any]:
        llm_map: dict[str, Any] = {}
        for name, binding in ir.providers.items():
            if self._provider_registry is not None:
                provider = self._provider_registry.get(binding.provider)
                if provider is not None:
                    llm_map[name] = provider
                    if binding.fallback_ref:
                        diagnostics.append(
                            CompileDiagnostic(
                                code=ROUTING_UNSUPPORTED,
                                path=f"providers.{name}.fallback_ref",
                                detail=(
                                    f"fallback_ref='{binding.fallback_ref}' is not "
                                    "auto-enforced; wire routing manually via the "
                                    "provider_registry."
                                ),
                            )
                        )
                    continue
            llm_map[name] = MockLLM(responses=[f"[{binding.model}] Mock response"])
            logger.debug("Using MockLLM for provider '%s' (model=%s)", name, binding.model)
        return llm_map

    def _build_agents(self, ir: BlueprintIR, llm_map: dict[str, Any]) -> dict[str, Agent]:
        agent_map: dict[str, Agent] = {}
        for name, agent_ir in ir.agents.items():
            llm = llm_map.get(agent_ir.provider, MockLLM(responses=["Mock response"]))
            agent_map[name] = Agent(name=name, llm=llm, system_prompt=agent_ir.prompt)
        return agent_map

    def _build_workflows(
        self,
        ir: BlueprintIR,
        agent_map: dict[str, Agent],
        diagnostics: list[CompileDiagnostic],
        intent: dict[str, str],
    ) -> dict[str, Any]:
        from pyagent_patterns.registry import get_pattern_class

        workflows: dict[str, Any] = {}
        for wf_name, wf_ir in ir.workflows.items():
            # "single" is not a registered pyagent_patterns pattern — it's
            # the degenerate no-orchestration case the conformance suite
            # exercises. Lower it onto `pipeline` with one stage, since
            # that's structurally the closest registered primitive; the
            # *intent* ("single", no orchestration) is preserved via the
            # `intent` map regardless of which pattern class runs it.
            lookup_name = "pipeline" if wf_ir.pattern == "single" else wf_ir.pattern
            pattern_cls = get_pattern_class(lookup_name)
            if pattern_cls is None:
                raise PyAgentCompilationError(
                    f"Unknown pattern '{wf_ir.pattern}' in workflow '{wf_name}'"
                )

            intent[wf_name] = wf_ir.pattern

            try:
                pattern = self._instantiate_pattern(
                    pattern_cls,
                    lookup_name,
                    wf_ir.agents,
                    agent_map,
                    wf_ir.config,
                    original_pattern=wf_ir.pattern,
                    wf_name=wf_name,
                )
            except Exception as exc:
                raise PyAgentCompilationError(
                    f"Failed to instantiate pattern '{wf_ir.pattern}' "
                    f"for workflow '{wf_name}': {exc}"
                ) from exc

            if wf_ir.recovery is not None:
                diagnostics.append(
                    CompileDiagnostic(
                        code=RECOVERY_UNSUPPORTED,
                        path=f"workflows.{wf_name}.recovery",
                        detail=(
                            "Recovery policy (retries/timeout/fallback) is not "
                            "auto-enforced by the compiled RuntimeGraph; caller must "
                            "implement retry/timeout/fallback around graph.run()."
                        ),
                    )
                )
            if wf_ir.guardrails:
                diagnostics.append(
                    CompileDiagnostic(
                        code=GUARDRAIL_UNSUPPORTED,
                        path=f"workflows.{wf_name}.guardrails",
                        detail=f"Guardrails {list(wf_ir.guardrails)} declared but not enforced.",
                    )
                )

            workflows[wf_name] = pattern

        return workflows

    @staticmethod
    def _resolve_ref(ref: Any, agent_map: dict[str, Agent], wf_name: str) -> Any:
        """Recursively resolve agent-name strings to `Agent` objects.

        Handles arbitrarily nested list/dict shapes (e.g. a hierarchical
        pattern's `teams: [{lead: ..., workers: [...]}]`) so every string
        that isn't itself a nested structural key (`name`, `reads`,
        `writes`, ...) resolves against `agent_map`.
        """
        if isinstance(ref, str):
            if ref not in agent_map:
                raise PyAgentCompilationError(
                    f"Agent ref '{ref}' in workflow '{wf_name}' not found. "
                    f"Available: {list(agent_map.keys())}"
                )
            return agent_map[ref]
        if isinstance(ref, list):
            return [PyAgentAdapter._resolve_ref(item, agent_map, wf_name) for item in ref]
        if isinstance(ref, dict):
            return {k: PyAgentAdapter._resolve_ref(v, agent_map, wf_name) for k, v in ref.items()}
        return ref

    @staticmethod
    def _instantiate_pattern(
        pattern_cls: type,
        pattern_name: str,
        agents_config: dict[str, Any],
        agent_map: dict[str, Agent],
        config: dict[str, Any],
        *,
        original_pattern: str | None = None,
        wf_name: str = "",
    ) -> Any:
        # Governance-only keys are diagnostic signals (reported by
        # `_diagnose_ungoverned_features`), never native pattern
        # constructor arguments — passing them through as **kwargs
        # crashes instantiation the moment a workflow declares one
        # (see tests/adapters: test_diagnostic_completeness_per_governance_feature).
        config = {k: v for k, v in config.items() if k not in _GOVERNANCE_ONLY_CONFIG_KEYS}

        def resolve(ref: Any) -> Any:
            return PyAgentAdapter._resolve_ref(ref, agent_map, wf_name)

        if pattern_name == "pipeline":
            if original_pattern == "single":
                agents = {k: resolve(v) for k, v in agents_config.items()}
                solo = agents.get("agent") or next(iter(agents.values()), None)
                return pattern_cls(stages=[solo], **config)
            stages = agents_config.get("stages", agents_config)
            stages = resolve(stages)
            if isinstance(stages, dict):
                stages = list(stages.values())
            return pattern_cls(stages=stages, **config)

        if pattern_name == "supervisor":
            return pattern_cls(
                classifier=resolve(agents_config.get("classifier")),
                routes=resolve(agents_config.get("routes", {})),
                **config,
            )

        if pattern_name == "fan_out_fan_in":
            agent_list = agents_config.get("agents")
            if agent_list is None:
                agent_list = [v for k, v in agents_config.items() if k != "aggregator"]
            agent_list = resolve(agent_list)
            if isinstance(agent_list, dict):
                agent_list = list(agent_list.values())
            aggregator = resolve(agents_config.get("aggregator"))
            return pattern_cls(agents=agent_list, aggregator=aggregator, **config)

        if pattern_name == "voting":
            from pyagent_patterns.resolution.voting import VotingStrategy

            voters = agents_config.get("voters")
            if voters is None:
                voters = list(agents_config.values())
            voters = resolve(voters)
            if isinstance(voters, dict):
                voters = list(voters.values())
            if isinstance(config.get("strategy"), str):
                config = {**config, "strategy": VotingStrategy(config["strategy"])}
            return pattern_cls(voters=voters, **config)

        if pattern_name == "debate":
            debaters = agents_config.get("debaters")
            if debaters is None:
                debaters = [v for k, v in agents_config.items() if k != "judge"]
            debaters = resolve(debaters)
            if isinstance(debaters, dict):
                debaters = list(debaters.values())
            judge = resolve(agents_config.get("judge"))
            return pattern_cls(debaters=debaters, judge=judge, **config)

        if pattern_name == "hierarchical":
            from pyagent_patterns.orchestration.hierarchical import Team

            manager = resolve(agents_config.get("manager"))
            teams = [
                Team(
                    name=team_cfg["name"],
                    lead=resolve(team_cfg["lead"]),
                    workers=[resolve(w) for w in team_cfg.get("workers", [])],
                )
                for team_cfg in agents_config.get("teams", [])
            ]
            return pattern_cls(manager=manager, teams=teams, **config)

        if pattern_name == "orchestrator_workers":
            orchestrator = resolve(agents_config.get("orchestrator"))
            workers = [resolve(w) for w in agents_config.get("workers", [])]
            return pattern_cls(orchestrator=orchestrator, workers=workers, **config)

        if pattern_name == "blackboard":
            from pyagent_patterns.structural.blackboard import BlackboardAgent

            blackboard_agents = [
                BlackboardAgent(
                    agent=resolve(a_cfg["agent"]),
                    reads=list(a_cfg.get("reads", [])),
                    writes=list(a_cfg.get("writes", [])),
                )
                for a_cfg in agents_config.get("agents", [])
            ]
            return pattern_cls(agents=blackboard_agents, **config)

        if pattern_name == "layered":
            from pyagent_patterns.structural.layered import Layer

            layers = [
                Layer(
                    name=layer_cfg["name"],
                    agents=[resolve(a) for a in layer_cfg.get("agents", [])],
                )
                for layer_cfg in agents_config.get("layers", [])
            ]
            return pattern_cls(layers=layers, **config)

        if pattern_name == "topology" and isinstance(config.get("topology"), str):
            from pyagent_patterns.structural.topology import TopologyType

            config = {**config, "topology": TopologyType(config["topology"])}

        agents = {k: resolve(v) for k, v in agents_config.items()}
        try:
            return pattern_cls(**agents, **config)
        except TypeError:
            return pattern_cls(agents=list(agents.values()), **config)

    @staticmethod
    def _diagnose_ungoverned_features(
        ir: BlueprintIR, diagnostics: list[CompileDiagnostic]
    ) -> None:
        """Port of compiler.py's `_warn_unwired`, upgraded from log
        warnings to structured, machine-checkable diagnostics (G1-G8)."""
        for wf_name, contract in ir.contracts.items():
            if contract.sla.cost_max_usd:
                diagnostics.append(
                    CompileDiagnostic(
                        code=BUDGET_UNSUPPORTED,
                        path=f"contracts.{wf_name}.sla.cost_max_usd",
                        detail="Cost budget is not auto-enforced by the compiled RuntimeGraph.",
                    )
                )
            diagnostics.append(
                CompileDiagnostic(
                    code=SLA_UNSUPPORTED,
                    path=f"contracts.{wf_name}.sla",
                    detail="SLA (latency/cost/quality) is not auto-enforced; wire cost/latency tracking manually.",
                )
            )

        if ir.observability and ir.observability.cost_budget_daily_usd is not None:
            diagnostics.append(
                CompileDiagnostic(
                    code=BUDGET_UNSUPPORTED,
                    path="observability.cost_budget",
                    detail=(
                        "Cost budget declared but not auto-enforced; wire manually via "
                        "graph.wire_cost_tracker(tracker)."
                    ),
                )
            )

        if ir.memory is not None:
            if ir.memory.compression_policy != "none":
                diagnostics.append(
                    CompileDiagnostic(
                        code=MEMORY_TIER_UNSUPPORTED,
                        path="memory.compression_policy",
                        detail=(
                            f"compression.policy='{ir.memory.compression_policy}' declared but "
                            "not auto-wired; call graph.wire_compressor(compressor)."
                        ),
                    )
                )
            if ir.memory.semantic_enabled:
                diagnostics.append(
                    CompileDiagnostic(
                        code=MEMORY_TIER_UNSUPPORTED,
                        path="memory.semantic_enabled",
                        detail="Semantic memory declared but not auto-wired; call graph.wire_context(ledger).",
                    )
                )
            if ir.memory.redaction_max_sensitivity is not None:
                diagnostics.append(
                    CompileDiagnostic(
                        code=MEMORY_TIER_UNSUPPORTED,
                        path="memory.redaction_max_sensitivity",
                        detail="Redaction policy declared but must be applied manually before sending to agents.",
                    )
                )

        for agent_name, agent_ir in ir.agents.items():
            if agent_ir.guardrails:
                diagnostics.append(
                    CompileDiagnostic(
                        code=GUARDRAIL_UNSUPPORTED,
                        path=f"agents.{agent_name}.guardrails",
                        detail=f"Guardrails {list(agent_ir.guardrails)} declared but not enforced.",
                    )
                )

        # G6 — no HITL checkpoint concept exists in the native runtime today.
        for wf_name, wf in ir.workflows.items():
            if wf.config.get("human_in_the_loop") or wf.config.get("checkpoint"):
                diagnostics.append(
                    CompileDiagnostic(
                        code=CHECKPOINT_UNSUPPORTED,
                        path=f"workflows.{wf_name}.config.human_in_the_loop",
                        detail="Workflow-level HITL checkpoint declared but not enforced by this adapter.",
                    )
                )
