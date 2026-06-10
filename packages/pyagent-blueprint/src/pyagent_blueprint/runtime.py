"""RuntimeGraph: executable DAG of compiled patterns."""

from __future__ import annotations

from typing import Any, AsyncIterator

from pyagent_patterns.base import Pattern, Result


class RuntimeGraph:
    """Executable graph of compiled workflows.

    Each workflow is a fully wired ``Pattern`` instance ready to run.

    Args:
        workflows: Mapping of workflow name → compiled Pattern.
        metadata: Blueprint metadata dict.
    """

    def __init__(
        self,
        workflows: dict[str, Pattern],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._workflows = workflows
        self._metadata = metadata or {}

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
        }

    @property
    def workflow_names(self) -> list[str]:
        return list(self._workflows.keys())

    def __contains__(self, workflow: str) -> bool:
        return workflow in self._workflows
