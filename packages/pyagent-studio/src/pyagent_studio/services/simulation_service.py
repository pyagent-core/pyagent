"""SimulationService: run blueprints with MockLLM and collect results."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyagent_blueprint import BlueprintCompiler

if TYPE_CHECKING:
    from pyagent_blueprint.schema import BlueprintSpec
    from pyagent_trace.events import TraceEventBus


@dataclass
class SimulationResult:
    """Result of a single simulation run.

    Attributes:
        workflow: Workflow name.
        input_task: The task string.
        output: The pattern output.
        elapsed_ms: Wall-clock time in milliseconds.
        success: Whether the run succeeded.
        error: Error message on failure.
    """

    workflow: str
    input_task: str
    output: str = ""
    elapsed_ms: float = 0.0
    success: bool = True
    error: str | None = None


class SimulationService:
    """Run simulations against compiled blueprints.

    Uses ``MockLLM`` by default so no API keys are needed.
    """

    def __init__(
        self,
        compiler: BlueprintCompiler | None = None,
        event_bus: TraceEventBus | None = None,
        use_live: bool = False,
    ) -> None:
        self._compiler = compiler or BlueprintCompiler()
        self._event_bus = event_bus
        self._use_live = use_live

    async def run(
        self,
        spec: BlueprintSpec,
        workflow: str,
        task: str,
        use_live: bool | None = None,
    ) -> SimulationResult:
        """Run a single simulation.

        Args:
            spec: Blueprint spec.
            workflow: Workflow name to run.
            task: Input task string.

        Returns:
            ``SimulationResult`` with output and timing.
        """
        try:
            graph = self._compiler.compile(spec)
        except Exception as exc:
            return SimulationResult(
                workflow=workflow,
                input_task=task,
                success=False,
                error=f"Compilation failed: {exc}",
            )

        if self._event_bus:
            from pyagent_trace.events import TraceEvent

            self._event_bus.emit(
                TraceEvent(
                    timestamp=time.time(),
                    event_type="pattern_start",
                    pattern_type=workflow,
                    payload={
                        "task": task,
                        "live": use_live if use_live is not None else self._use_live,
                    },
                )
            )

        start = time.perf_counter()
        try:
            result = await graph.run(workflow, task)
            elapsed = (time.perf_counter() - start) * 1000
            return SimulationResult(
                workflow=workflow,
                input_task=task,
                output=result.output,
                elapsed_ms=elapsed,
                success=True,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return SimulationResult(
                workflow=workflow,
                input_task=task,
                elapsed_ms=elapsed,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    async def run_all(
        self,
        spec: BlueprintSpec,
        tasks: dict[str, str],
        use_live: bool | None = None,
    ) -> list[SimulationResult]:
        """Run simulations for multiple workflows.

        Args:
            spec: Blueprint spec.
            tasks: Mapping of workflow name → task string.

        Returns:
            List of simulation results.
        """
        results: list[SimulationResult] = []
        for workflow, task in tasks.items():
            result = await self.run(spec, workflow, task, use_live=use_live)
            results.append(result)
        return results
