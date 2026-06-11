"""RuntimeGraph: executable DAG of compiled patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pyagent_patterns.base import Agent, Pattern, Result


class RuntimeGraph:
    """Executable graph of compiled workflows.

    Each workflow is a fully wired ``Pattern`` instance ready to run.

    Args:
        workflows: Mapping of workflow name → compiled Pattern.
        agents: Mapping of agent name → Agent instance.
        metadata: Blueprint metadata dict.
    """

    def __init__(
        self,
        workflows: dict[str, Pattern],
        agents: dict[str, Agent] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._workflows = workflows
        self._agents = agents or {}
        self._metadata = metadata or {}

    # -- Hook-wiring convenience methods --

    def wire_trace(self, bus: Any) -> None:
        """Set trace_bus on all patterns and their agents.

        Args:
            bus: A ``TraceEventBus`` instance.
        """
        for pattern in self._workflows.values():
            pattern.set_trace_bus(bus)
        for agent in self._agents.values():
            agent.set_trace_bus(bus)

    def wire_context(self, ledger: Any) -> None:
        """Set context ledger on all agents in all workflows.

        Args:
            ledger: A ``ContextLedger`` instance.
        """
        for agent in self._agents.values():
            agent.set_context(ledger)

    def wire_compressor(self, compressor: Any) -> None:
        """Set compressor on all agents.

        Args:
            compressor: A ``MessageCompressor`` instance.
        """
        for agent in self._agents.values():
            agent.set_compressor(compressor)

    def wire_cost_tracker(self, tracker: Any) -> None:
        """Set cost tracker on all agents.

        Args:
            tracker: A ``CostTracker`` instance.
        """
        for agent in self._agents.values():
            agent.set_cost_tracker(tracker)

    # -- Execution --

    async def run(self, workflow: str, task: str) -> Result:
        """Run a workflow by name.

        Args:
            workflow: Workflow name from the blueprint.
            task: Input task string.

        Returns:
            Pattern ``Result``.

        Raises:
            KeyError: If workflow name doesn't exist.
        """
        if workflow not in self._workflows:
            available = list(self._workflows.keys())
            raise KeyError(f"Unknown workflow '{workflow}'. Available: {available}")

        pattern = self._workflows[workflow]
        return await pattern.run(task)

    async def stream(self, workflow: str, task: str) -> AsyncIterator[str]:
        """Stream results from a workflow.

        Falls back to ``run()`` and yields the full output if the pattern
        doesn't support native streaming.
        """
        result = await self.run(workflow, task)
        yield result.output

    def describe(self) -> dict[str, Any]:
        """Introspect the runtime graph.

        Returns:
            Dict with metadata and workflow descriptions.
        """
        return {
            "metadata": self._metadata,
            "workflows": {
                name: {
                    "pattern_type": type(pattern).__name__,
                }
                for name, pattern in self._workflows.items()
            },
            "agents": list(self._agents.keys()),
        }

    @property
    def workflow_names(self) -> list[str]:
        return list(self._workflows.keys())

    @property
    def agents(self) -> dict[str, Agent]:
        return dict(self._agents)

    def __contains__(self, workflow: str) -> bool:
        return workflow in self._workflows
