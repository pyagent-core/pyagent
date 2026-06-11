"""BlueprintRenderer: spec → Mermaid diagram or Markdown documentation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyagent_blueprint.schema.spec import BlueprintSpec


class BlueprintRenderer:
    """Render a BlueprintSpec as Mermaid diagrams or Markdown docs."""

    def to_mermaid(self, spec: BlueprintSpec) -> str:
        """Render the blueprint as a Mermaid flowchart.

        Args:
            spec: Blueprint specification.

        Returns:
            Mermaid diagram string.
        """
        lines = ["graph TD"]

        # Agent nodes
        for name, agent_spec in spec.agents.items():
            label = agent_spec.description or name
            lines.append(f"    {name}[{label}]")

        # Workflow edges
        for _, wf_spec in spec.workflows.items():
            agent_refs = self._extract_agent_refs(wf_spec.agents)
            if len(agent_refs) > 1:
                for i in range(len(agent_refs) - 1):
                    lines.append(f"    {agent_refs[i]} -->|{wf_spec.pattern}| {agent_refs[i + 1]}")

            # For supervisor-like patterns, show classifier → routes
            if "classifier" in wf_spec.agents and "routes" in wf_spec.agents:
                classifier = wf_spec.agents["classifier"]
                routes = wf_spec.agents.get("routes", {})
                if isinstance(routes, dict):
                    for route_name, route_ref in routes.items():
                        lines.append(f"    {classifier} -->|{route_name}| {route_ref}")

        return "\n".join(lines)

    def to_markdown(self, spec: BlueprintSpec) -> str:
        """Render the blueprint as Markdown documentation.

        Args:
            spec: Blueprint specification.

        Returns:
            Markdown string.
        """
        sections: list[str] = []

        # Title
        sections.append(f"# {spec.metadata.name}")
        if spec.metadata.description:
            sections.append(f"\n{spec.metadata.description}")
        sections.append(f"\n**Version:** {spec.metadata.version}")
        if spec.metadata.owner:
            sections.append(f"**Owner:** {spec.metadata.owner}")

        # Providers
        if spec.providers:
            sections.append("\n## Providers\n")
            for name, p in spec.providers.items():
                sections.append(f"- **{name}**: `{p.model}` ({p.provider})")

        # Agents
        sections.append("\n## Agents\n")
        for name, a in spec.agents.items():
            desc = a.description or "No description"
            sections.append(f"### {name}\n")
            sections.append(f"- **Description:** {desc}")
            sections.append(f"- **Prompt:** {a.prompt[:100]}{'...' if len(a.prompt) > 100 else ''}")
            if a.provider:
                sections.append(f"- **Provider:** {a.provider}")
            if a.guardrails:
                sections.append(f"- **Guardrails:** {', '.join(a.guardrails)}")

        # Workflows
        sections.append("\n## Workflows\n")
        for name, w in spec.workflows.items():
            sections.append(f"### {name}\n")
            sections.append(f"- **Pattern:** {w.pattern}")
            if w.recovery:
                sections.append(
                    f"- **Recovery:** max_retries={w.recovery.max_retries}, "
                    f"timeout={w.recovery.timeout_seconds}s"
                )

        # Contracts
        if spec.contracts:
            sections.append("\n## Contracts\n")
            for name, c in spec.contracts.items():
                sections.append(f"### {name}\n")
                sections.append(
                    f"- **SLA:** p95 latency ≤ {c.sla.latency_p95_ms}ms, "
                    f"cost ≤ ${c.sla.cost_max_usd}"
                )

        # Diagram
        sections.append("\n## Architecture Diagram\n")
        sections.append("```mermaid")
        sections.append(self.to_mermaid(spec))
        sections.append("```")

        return "\n".join(sections)

    @staticmethod
    def _extract_agent_refs(agents: dict) -> list[str]:
        """Flatten agent refs from a workflow's agents dict."""
        refs: list[str] = []
        for _, ref in agents.items():
            if isinstance(ref, str):
                refs.append(ref)
            elif isinstance(ref, dict):
                refs.extend(ref.values())
        return refs
