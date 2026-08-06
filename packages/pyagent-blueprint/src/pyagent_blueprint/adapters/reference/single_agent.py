"""SingleAgentAdapter: the degenerate case — no orchestration whatsoever.

One LLM call, one response, no workflow concept beyond "run this one
agent." If the `RuntimeAdapter` contract can't cleanly express "there is
no graph, just an agent," it's over-designed for orchestration and
under-designed for the simple 80% use case (see
TRANSFORMATION-PLAN.md Section 6).

Declares `Capability.SYNC_EXECUTION` to exercise the conformance suite's
sync-adapter-still-awaitable check — this adapter's "native" call is a
plain synchronous function, wrapped for the async contract.
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


class SingleAgentHandle:
    """Opaque compiled artifact: workflow name -> (agent_name, prompt)."""

    def __init__(self, workflows: dict[str, tuple[str, str]]) -> None:
        self.workflows = workflows


def _sync_call(agent_name: str, prompt: str, input_: str) -> str:
    """A plainly synchronous "native call" — this adapter's run() wraps
    this, simulating an SDK whose core API is sync-only."""
    return mock_call(agent_name, prompt, input_)


class SingleAgentAdapter(RuntimeAdapter):
    """No orchestration at all — one agent, one call, one response."""

    name = "single_agent"
    capabilities = Capability.SYNC_EXECUTION

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics = diagnose_common_governance(ir)
        intent: dict[str, str] = {}
        workflows: dict[str, tuple[str, str]] = {}

        for wf_name, wf in ir.workflows.items():
            intent[wf_name] = wf.pattern
            refs = flatten_agent_refs(wf.agents)
            if not refs:
                continue
            # Degenerate by design: only the FIRST agent ref is honored,
            # regardless of how many are declared — this adapter has no
            # concept of "more than one agent in a workflow."
            agent_name = refs[0]
            agent_ir = ir.agents.get(agent_name)
            prompt = agent_ir.prompt if agent_ir else ""
            workflows[wf_name] = (agent_name, prompt)

        return CompiledArtifact(
            handle=SingleAgentHandle(workflows), diagnostics=diagnostics, intent=intent
        )

    async def run(
        self, compiled: CompiledArtifact, workflow: str, input_: str, **kwargs: Any
    ) -> AdapterResult:
        handle: SingleAgentHandle = compiled.handle
        if workflow not in handle.workflows:
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow}'. Available: {list(handle.workflows)}"
            )
        agent_name, prompt = handle.workflows[workflow]
        # The "native" call is sync; RuntimeAdapter.run() is still async
        # from the caller's perspective — this adapter does the wrapping.
        output = _sync_call(agent_name, prompt, input_)
        return AdapterResult(output=output, raw={"agent": agent_name})

    def supported_patterns(self) -> list[str]:
        # No fixed pattern vocabulary — this adapter treats every
        # workflow the same way (pick the first agent, ignore the rest).
        return []
