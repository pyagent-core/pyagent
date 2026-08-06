"""BlueprintGenerator: scaffold YAML from pattern name + agent descriptions."""

from __future__ import annotations

import yaml


def _resolve_pattern_vocabulary(adapter_name: str | None) -> tuple[set[str], object | None]:
    """Return (known pattern names, adapter instance or None).

    If `adapter_name` is given, resolve that specific adapter via the
    registry (raises if not installed). If not given, try any installed
    adapter; if none is installed, fall back to an empty vocabulary
    (scaffolding still works — the generated YAML just isn't validated
    against a known pattern list).
    """
    from pyagent_blueprint.adapter import AdapterRegistry

    if adapter_name is not None:
        adapter_cls = AdapterRegistry.get(adapter_name)
        adapter = adapter_cls()
        return set(adapter.supported_patterns()), adapter

    adapters = AdapterRegistry.discover()
    for adapter_cls in adapters.values():
        adapter = adapter_cls()
        patterns = set(adapter.supported_patterns())
        if patterns:
            return patterns, adapter
    return set(), None


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
        adapter: str | None = None,
    ) -> str:
        """Generate a blueprint YAML string.

        Args:
            pattern: Pattern registry name (e.g., ``"supervisor"``, ``"pipeline"``).
            agents: List of agent names.
            name: Blueprint name.
            version: Blueprint version.
            description: Blueprint description.
            adapter: Optional adapter entry-point name to validate `pattern`
                against. If omitted, any installed adapter's vocabulary is
                used; if none is installed, the pattern name isn't checked
                at all — scaffolding still works with zero runtime packages
                installed.

        Returns:
            YAML string.

        Raises:
            ValueError: If a pattern vocabulary is available (from the
                resolved adapter, or any installed adapter) and `pattern`
                isn't in it.
        """
        known, _resolved_adapter = _resolve_pattern_vocabulary(adapter)
        if known and pattern not in known:
            raise ValueError(f"Unknown pattern '{pattern}'. Available: {sorted(known)}")

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
