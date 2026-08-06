"""SimpleLoopAdapter: bare `while` loop, manual OpenAI-style
function-calling, NO framework, no graph library at all.

The cheapest way to disprove "the interface secretly requires a DAG."
Zero external dependency — can run in CI unconditionally (see
TRANSFORMATION-PLAN.md Section 6).

Declares `Capability.STREAMING` to exercise the conformance suite's
streaming-consistency check — this adapter "streams" by yielding each
agent's mock output chunk as it completes its turn in the loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyagent_blueprint.adapter import (
    AdapterResult,
    Capability,
    CompiledArtifact,
    RuntimeAdapter,
    UnknownWorkflowError,
)
from pyagent_blueprint.adapters.reference._common import (
    diagnose_common_governance,
    flatten_agent_refs,
    mock_call,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pyagent_blueprint.ir import BlueprintIR

#: Hard ceiling so a misconfigured blueprint can never spin forever —
#: this is the loop-based adapter's only nod to "recovery," and it's a
#: structural safety net, not a declared Capability.
MAX_ITERATIONS = 25


class SimpleLoopHandle:
    """Opaque compiled artifact: workflow name -> ordered [(agent_name, prompt), ...]."""

    def __init__(self, loops: dict[str, list[tuple[str, str]]]) -> None:
        self.loops = loops


class SimpleLoopAdapter(RuntimeAdapter):
    """Bare while-loop function-calling style — no graph, no chain
    abstraction, no framework. Just iterate agents and call each in
    turn, bounded by MAX_ITERATIONS."""

    name = "simple_loop"
    capabilities = Capability.STREAMING

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics = diagnose_common_governance(ir)
        intent: dict[str, str] = {}
        loops: dict[str, list[tuple[str, str]]] = {}

        for wf_name, wf in ir.workflows.items():
            intent[wf_name] = wf.pattern
            ordered_refs = flatten_agent_refs(wf.agents)
            steps: list[tuple[str, str]] = []
            for agent_name in ordered_refs:
                agent_ir = ir.agents.get(agent_name)
                steps.append((agent_name, agent_ir.prompt if agent_ir else ""))
            loops[wf_name] = steps

        return CompiledArtifact(
            handle=SimpleLoopHandle(loops), diagnostics=diagnostics, intent=intent
        )

    async def run(
        self, compiled: CompiledArtifact, workflow: str, input_: str, **kwargs: Any
    ) -> AdapterResult:
        handle: SimpleLoopHandle = compiled.handle
        if workflow not in handle.loops:
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow}'. Available: {list(handle.loops)}"
            )

        steps = handle.loops[workflow]
        current = input_
        turns = 0
        i = 0
        # Bare while-loop, manual iteration — no graph object, no
        # framework call, just plain Python control flow.
        while i < len(steps) and turns < MAX_ITERATIONS:
            agent_name, prompt = steps[i]
            current = mock_call(agent_name, prompt, current)
            i += 1
            turns += 1

        return AdapterResult(output=current, raw={"turns": turns})

    async def stream(
        self, compiled: CompiledArtifact, workflow: str, input_: str, **kwargs: Any
    ) -> AsyncIterator[Any]:
        handle: SimpleLoopHandle = compiled.handle
        if workflow not in handle.loops:
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow}'. Available: {list(handle.loops)}"
            )

        steps = handle.loops[workflow]
        current = input_
        turns = 0
        i = 0
        while i < len(steps) and turns < MAX_ITERATIONS:
            agent_name, prompt = steps[i]
            current = mock_call(agent_name, prompt, current)
            yield current
            i += 1
            turns += 1

    def supported_patterns(self) -> list[str]:
        return []
