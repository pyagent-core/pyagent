"""BlueprintGenerator: scaffold YAML from pattern name + agent descriptions."""

from __future__ import annotations

import yaml
from pyagent_patterns.registry import get_pattern_class, list_patterns


class BlueprintGenerator:
    """Generate scaffold blueprint YAML from a pattern name and agent list.

    Args:
        default_provider_model: Model to use in the default provider binding.
    """

    def __init__(self, default_provider_model: str = "gpt-4.1-mini") -> None:
        self._default_model = default_provider_model

    def generate(
        self,
        pattern: str,
        agents: list[str],
        *,
        name: str = "my-blueprint",
        version: str = "0.1.0",
        description: str = "",
    ) -> str:
        """Generate a blueprint YAML string.

        Args:
            pattern: Pattern registry name (e.g., ``"supervisor"``, ``"pipeline"``).
            agents: List of agent names.
            name: Blueprint name.
            version: Blueprint version.
            description: Blueprint description.

        Returns:
            YAML string.

        Raises:
            ValueError: If the pattern is not registered.
        """
        if get_pattern_class(pattern) is None:
            available = list_patterns()
            raise ValueError(f"Unknown pattern '{pattern}'. Available: {available}")

        spec: dict = {
            "api_version": "pyagent/v1",
            "metadata": {
                "name": name,
                "version": version,
                "description": description or f"A {pattern} blueprint",
            },
            "providers": {
                "primary": {"model": self._default_model},
            },
            "agents": {},
            "workflows": {},
        }

        # Generate agent specs
        for agent_name in agents:
            spec["agents"][agent_name] = {
                "prompt": f"You are the {agent_name} agent. TODO: add your prompt here.",
                "provider": "primary",
            }

        # Generate workflow spec
        wf_agents = self._wire_pattern_agents(pattern, agents)
        spec["workflows"]["main"] = {
            "pattern": pattern,
            "agents": wf_agents,
        }

        return yaml.dump(spec, default_flow_style=False, sort_keys=False)

    @staticmethod
    def _wire_pattern_agents(pattern: str, agents: list[str]) -> dict:
        """Create the agents mapping for a workflow based on pattern type."""
        if pattern == "supervisor" and len(agents) >= 2:
            return {
                "classifier": agents[0],
                "routes": {name: name for name in agents[1:]},
            }

        if pattern == "pipeline":
            return {"stages": {name: name for name in agents}}

        if pattern in ("fan_out_fan_in", "voting", "debate"):
            return {"agents": {name: name for name in agents}}

        if pattern in ("self_reflection", "evaluator_optimizer") and len(agents) >= 2:
            return {
                "generator": agents[0],
                "evaluator": agents[1],
            }

        if pattern == "cross_reflection" and len(agents) >= 2:
            return {
                "agent_a": agents[0],
                "agent_b": agents[1],
            }

        # Default: pass all agents
        return {name: name for name in agents}
