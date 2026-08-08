"""OpenAIAgentsAdapter: a real (not stubbed) pyagent-blueprint RuntimeAdapter
targeting the OpenAI Agents SDK (`agents` package).

Ships inside `pyagent-blueprint` behind the optional `openai-agents`
extra (`pip install "pyagent-blueprint[openai-agents]"`) — the `agents`
package is never a core dependency, and `AdapterRegistry.discover()`
skips this adapter gracefully when it isn't installed. Certified against
the shared `AdapterConformanceSuite`.

The OpenAI Agents SDK is handoff/turn-based (an `Agent` + a `Runner` that
executes turns, not a declared graph) — structurally distinct from
LangGraph's node/edge graph model, which is exactly the kind of second,
dissimilar proof point the plan calls for.

To keep this adapter fully offline-testable (no API key / network
required), each compiled agent is bound to a deterministic `FakeModel`
that returns `mock_call(...)`'s output via the SDK's real
`ModelResponse`/`ResponseOutputMessage` types — so the adapter exercises
the SDK's actual `Runner.run()` execution path, not a bypass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agents import Agent, Model, ModelResponse, Runner, Usage
from openai.types.responses import ResponseOutputMessage, ResponseOutputText

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


class _FakeDeterministicModel(Model):
    """A `Model` implementation with no network dependency.

    Returns `mock_call(agent_name, prompt, ...)`'s output through the
    SDK's real `ModelResponse`/`ResponseOutputMessage` types, so
    `Runner.run()` executes its actual turn-processing logic against a
    deterministic, offline-safe response.
    """

    def __init__(self, agent_name: str, prompt: str) -> None:
        self._agent_name = agent_name
        self._prompt = prompt

    async def get_response(
        self,
        system_instructions,
        input,
        model_settings,
        tools,
        output_schema,
        handoffs,
        tracing,
        *,
        previous_response_id,
        conversation_id,
        prompt,
    ) -> ModelResponse:
        text_input = input if isinstance(input, str) else str(input)
        text = mock_call(self._agent_name, self._prompt, text_input)
        message = ResponseOutputMessage(
            id=f"msg_{self._agent_name}",
            content=[ResponseOutputText(text=text, type="output_text", annotations=[])],
            role="assistant",
            status="completed",
            type="message",
        )
        return ModelResponse(output=[message], usage=Usage(), response_id=None)

    async def stream_response(self, *args: Any, **kwargs: Any):
        raise NotImplementedError("Streaming is not exercised by this adapter")


class OpenAIAgentsHandle:
    """Opaque compiled artifact: workflow name -> ordered list of Agent instances."""

    def __init__(self, workflows: dict[str, list[Agent]]) -> None:
        self.workflows = workflows


class OpenAIAgentsAdapter(RuntimeAdapter):
    """Compiles each blueprint workflow into a chain of OpenAI Agents SDK
    `Agent` instances, executed in sequence via `Runner.run()`.

    Every agent referenced by a workflow (agent-ref order, resolved via
    `flatten_agent_refs`) becomes one `Agent`, each bound to a
    deterministic offline `Model`. `run()` chains each agent's
    `final_output` into the next agent's input — the handoff/turn-based
    equivalent of `SequentialChainAdapter`'s linear pipeline, but through
    the SDK's real `Agent`/`Runner` execution engine.
    """

    name = "openai_agents"
    capabilities = Capability.NONE

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics = diagnose_common_governance(ir)
        intent: dict[str, str] = {}
        workflows: dict[str, list[Agent]] = {}

        for wf_name, wf in ir.workflows.items():
            intent[wf_name] = wf.pattern
            refs = flatten_agent_refs(wf.agents)

            chain: list[Agent] = []
            for agent_name in refs:
                agent_ir = ir.agents.get(agent_name)
                prompt = agent_ir.prompt if agent_ir else ""
                chain.append(
                    Agent(
                        name=agent_name,
                        instructions=prompt,
                        model=_FakeDeterministicModel(agent_name, prompt),
                    )
                )
            workflows[wf_name] = chain

        return CompiledArtifact(
            handle=OpenAIAgentsHandle(workflows), diagnostics=diagnostics, intent=intent
        )

    async def run(self, artifact: CompiledArtifact, workflow: str, input_: str) -> AdapterResult:
        handle: OpenAIAgentsHandle = artifact.handle
        chain = handle.workflows.get(workflow)
        if chain is None:
            raise UnknownWorkflowError(f"Unknown workflow: {workflow!r}")

        current_input = input_
        trace: list[str] = []
        for sdk_agent in chain:
            result = await Runner.run(sdk_agent, current_input)
            current_input = result.final_output
            trace.append(sdk_agent.name)

        return AdapterResult(
            output=current_input,
            raw=trace,
            usage={"agents_executed": len(trace)},
        )
