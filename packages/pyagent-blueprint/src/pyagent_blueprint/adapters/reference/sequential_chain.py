"""SequentialChainAdapter: strict linear pipeline, no branching, no
shared state object at all.

Output of agent N is verbatim input to agent N+1. Proves the contract
doesn't assume branching/routing exists — the minimal possible
non-degenerate topology (see TRANSFORMATION-PLAN.md Section 6).

Declares NO capabilities — the deliberate baseline for "what's the
absolute floor of what an adapter must support."
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
    from pyagent_blueprint.ir import BlueprintIR


class SequentialChainHandle:
    """Opaque compiled artifact: workflow name -> ordered [(agent_name, prompt), ...]."""

    def __init__(self, chains: dict[str, list[tuple[str, str]]]) -> None:
        self.chains = chains


class SequentialChainAdapter(RuntimeAdapter):
    """Strict linear pipeline: stage N's output IS stage N+1's input,
    verbatim, with no shared state and no branching whatsoever."""

    name = "sequential_chain"
    capabilities = Capability.NONE

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics = diagnose_common_governance(ir)
        intent: dict[str, str] = {}
        chains: dict[str, list[tuple[str, str]]] = {}

        for wf_name, wf in ir.workflows.items():
            intent[wf_name] = wf.pattern
            ordered_refs = flatten_agent_refs(wf.agents)
            chain: list[tuple[str, str]] = []
            for agent_name in ordered_refs:
                agent_ir = ir.agents.get(agent_name)
                chain.append((agent_name, agent_ir.prompt if agent_ir else ""))
            chains[wf_name] = chain

        return CompiledArtifact(
            handle=SequentialChainHandle(chains), diagnostics=diagnostics, intent=intent
        )

    async def run(
        self, compiled: CompiledArtifact, workflow: str, input_: str, **kwargs: Any
    ) -> AdapterResult:
        handle: SequentialChainHandle = compiled.handle
        if workflow not in handle.chains:
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow}'. Available: {list(handle.chains)}"
            )

        current = input_
        stage_outputs: list[str] = []
        for agent_name, prompt in handle.chains[workflow]:
            current = mock_call(agent_name, prompt, current)
            stage_outputs.append(current)

        return AdapterResult(output=current, raw={"stage_outputs": stage_outputs})

    def supported_patterns(self) -> list[str]:
        # No fixed vocabulary — every workflow is treated as "a chain",
        # regardless of what pattern name the blueprint declares.
        return []
