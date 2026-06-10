"""BlueprintCompiler: spec → RuntimeGraph (DAG of Pattern instances)."""

from __future__ import annotations

import logging
from typing import Any

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.registry import get_pattern_class
from pyagent_blueprint.runtime import RuntimeGraph
from pyagent_blueprint.schema.spec import BlueprintSpec

logger = logging.getLogger(__name__)


class CompilationError(Exception):
    """Raised when a blueprint cannot be compiled."""


class BlueprintCompiler:
    """Compile a BlueprintSpec into a RuntimeGraph.

    Steps:
    1. Resolve provider bindings → LLMCallable instances
    2. Instantiate agents with resolved LLMs
    3. Look up pattern class from registry
    4. Wire agents into pattern constructor kwargs
    5. Return RuntimeGraph

    Args:
        provider_registry: Optional ``ProviderRegistry`` for real providers.
            If ``None``, uses ``MockLLM`` for all providers.
    """

    def __init__(self, provider_registry: Any = None) -> None:
        self._provider_registry = provider_registry

    def compile(self, spec: BlueprintSpec) -> RuntimeGraph:
        """Compile a blueprint spec into a runnable RuntimeGraph.

        Args:
            spec: Validated ``BlueprintSpec``.

        Returns:
            ``RuntimeGraph`` ready to execute.

        Raises:
            CompilationError: If the spec references unknown patterns or agents.
        """
        # Step 1: Resolve providers → LLMCallable
        llm_map = self._resolve_providers(spec)

        # Step 2: Instantiate agents
        agent_map = self._build_agents(spec, llm_map)

        # Step 3 & 4: Wire patterns
        workflows = self._build_workflows(spec, agent_map)

        metadata = spec.metadata.model_dump() if spec.metadata else {}
        return RuntimeGraph(workflows=workflows, metadata=metadata)

    def _resolve_providers(self, spec: BlueprintSpec) -> dict[str, Any]:
        """Map provider names to LLMCallable instances."""
        llm_map: dict[str, Any] = {}

        for name, binding in spec.providers.items():
            if self._provider_registry is not None:
                provider = self._provider_registry.get(binding.provider)
                if provider is not None:
                    llm_map[name] = provider
                    continue

            # Fallback: MockLLM
            llm_map[name] = MockLLM(responses=[f"[{binding.model}] Mock response"])
            logger.debug("Using MockLLM for provider '%s' (model=%s)", name, binding.model)

        return llm_map

    def _build_agents(
        self,
        spec: BlueprintSpec,
        llm_map: dict[str, Any],
    ) -> dict[str, Agent]:
        """Instantiate Agent objects from spec."""
        agent_map: dict[str, Agent] = {}

        for name, agent_spec in spec.agents.items():
            llm = llm_map.get(agent_spec.provider, MockLLM(responses=["Mock response"]))
            agent_map[name] = Agent(
                name=name,
                llm=llm,
                system_prompt=agent_spec.prompt,
            )

        return agent_map

    def _build_workflows(
        self,
        spec: BlueprintSpec,
        agent_map: dict[str, Agent],
    ) -> dict[str, Any]:
        """Look up pattern classes and wire agents."""
        from pyagent_patterns.orchestration import Pipeline

        workflows: dict[str, Any] = {}

        for wf_name, wf_spec in spec.workflows.items():
            pattern_cls = get_pattern_class(wf_spec.pattern)
            if pattern_cls is None:
                raise CompilationError(
                    f"Unknown pattern '{wf_spec.pattern}' in workflow '{wf_name}'"
                )

            # Resolve agent refs
            wired_agents = self._resolve_agent_refs(wf_spec.agents, agent_map, wf_name)

            # Try to instantiate the pattern
            try:
                pattern = self._instantiate_pattern(
                    pattern_cls, wf_spec.pattern, wired_agents, wf_spec.config
                )
            except Exception as exc:
                raise CompilationError(
                    f"Failed to instantiate pattern '{wf_spec.pattern}' "
                    f"for workflow '{wf_name}': {exc}"
                ) from exc

            workflows[wf_name] = pattern

        return workflows

    def _resolve_agent_refs(
        self,
        agents_config: dict[str, Any],
        agent_map: dict[str, Agent],
        wf_name: str,
    ) -> dict[str, Any]:
        """Resolve agent name references to Agent objects."""
        resolved: dict[str, Any] = {}
        for role, ref in agents_config.items():
            if isinstance(ref, str):
                if ref not in agent_map:
                    raise CompilationError(
                        f"Agent ref '{ref}' in workflow '{wf_name}' not found. "
                        f"Available: {list(agent_map.keys())}"
                    )
                resolved[role] = agent_map[ref]
            elif isinstance(ref, dict):
                # Nested refs (e.g., routes: {billing: billing_agent})
                resolved[role] = {
                    k: agent_map[v] if v in agent_map else v
                    for k, v in ref.items()
                }
            else:
                resolved[role] = ref
        return resolved

    @staticmethod
    def _instantiate_pattern(
        pattern_cls: type,
        pattern_name: str,
        agents: dict[str, Any],
        config: dict[str, Any],
    ) -> Any:
        """Instantiate a pattern from resolved agents and config.

        Handles the common pattern constructor signatures.
        """
        # Pipeline: expects `stages` list
        if pattern_name == "pipeline":
            stages = agents.get("stages", list(agents.values()))
            if isinstance(stages, dict):
                stages = list(stages.values())
            return pattern_cls(stages=stages, **config)

        # Supervisor: expects `classifier` + `routes`
        if pattern_name == "supervisor":
            return pattern_cls(
                classifier=agents.get("classifier"),
                routes=agents.get("routes", {}),
                **config,
            )

        # Fan-out/fan-in: expects `agents` list
        if pattern_name in ("fan_out_fan_in", "voting", "debate"):
            agent_list = list(agents.values())
            if len(agent_list) == 1 and isinstance(agent_list[0], dict):
                agent_list = list(agent_list[0].values())
            return pattern_cls(agents=agent_list, **config)

        # Default: pass agents dict as kwargs
        try:
            return pattern_cls(**agents, **config)
        except TypeError:
            # Try with agents as a list
            return pattern_cls(agents=list(agents.values()), **config)
