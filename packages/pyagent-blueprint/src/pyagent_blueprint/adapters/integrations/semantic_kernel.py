"""SemanticKernelAdapter: a real (not stubbed) pyagent-blueprint
RuntimeAdapter targeting Microsoft Semantic Kernel.

Ships inside `pyagent-blueprint` behind the optional `semantic-kernel`
extra (`pip install "pyagent-blueprint[semantic-kernel]"`) — the
`semantic-kernel` package is never a core dependency, and
`AdapterRegistry.discover()` skips this adapter gracefully when it isn't
installed. Certified against the shared `AdapterConformanceSuite`.

Semantic Kernel is event/service-oriented: a `Kernel` hosts pluggable
AI services, and `ChatCompletionAgent`s are bound to a
`ChatCompletionClientBase` service. This is a fourth structurally
distinct model — neither a declared graph, handoff/turn-based, nor
role-based — completing the diversity of proof points called for by
the plan.

To keep this adapter fully offline-testable (no API key / network
required), each agent's service is a deterministic
`ChatCompletionClientBase` subclass that returns `mock_call(...)`'s
output via the SDK's real `ChatMessageContent` type — so the adapter
exercises Semantic Kernel's actual `ChatCompletionAgent.get_response()`
execution path, not a bypass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents import AuthorRole, ChatHistory, ChatMessageContent

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


class _FakeDeterministicService(ChatCompletionClientBase):
    """A `ChatCompletionClientBase` implementation with no network
    dependency. Returns `mock_call(...)`'s output through the SDK's real
    `ChatMessageContent` type, letting `ChatCompletionAgent.get_response()`
    run its actual message-handling path against a deterministic,
    offline-safe response.
    """

    _agent_name: str = ""
    _prompt: str = ""

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: PromptExecutionSettings
    ) -> list[ChatMessageContent]:
        last_user = ""
        for message in reversed(chat_history.messages):
            if message.role == AuthorRole.USER:
                last_user = str(message.content)
                break
        text = mock_call(self._agent_name, self._prompt, last_user or self._prompt)
        return [ChatMessageContent(role=AuthorRole.ASSISTANT, content=text)]

    def get_prompt_execution_settings_class(self) -> type[PromptExecutionSettings]:
        return PromptExecutionSettings


def _make_agent(agent_name: str, prompt: str) -> ChatCompletionAgent:
    service = _FakeDeterministicService(ai_model_id=f"fake-{agent_name}")
    object.__setattr__(service, "_agent_name", agent_name)
    object.__setattr__(service, "_prompt", prompt)
    return ChatCompletionAgent(name=agent_name, instructions=prompt, service=service)


class SemanticKernelHandle:
    """Opaque compiled artifact: workflow name -> ordered list of ChatCompletionAgents."""

    def __init__(self, workflows: dict[str, list[ChatCompletionAgent]]) -> None:
        self.workflows = workflows


class SemanticKernelAdapter(RuntimeAdapter):
    """Compiles each blueprint workflow into a chain of Semantic Kernel
    `ChatCompletionAgent`s, executed in sequence.

    Every agent referenced by a workflow (agent-ref order, resolved via
    `flatten_agent_refs`) becomes one `ChatCompletionAgent`, each bound
    to a deterministic offline service. `run()` chains each agent's
    response text into the next agent's input message — the
    service-oriented equivalent of `SequentialChainAdapter`'s linear
    pipeline, executed through Semantic Kernel's real agent/service
    execution engine.
    """

    name = "semantic_kernel"
    capabilities = Capability.NONE

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics = diagnose_common_governance(ir)
        intent: dict[str, str] = {}
        workflows: dict[str, list[ChatCompletionAgent]] = {}

        for wf_name, wf in ir.workflows.items():
            intent[wf_name] = wf.pattern
            refs = flatten_agent_refs(wf.agents)

            chain: list[ChatCompletionAgent] = []
            for agent_name in refs:
                agent_ir = ir.agents.get(agent_name)
                prompt = agent_ir.prompt if agent_ir else ""
                chain.append(_make_agent(agent_name, prompt))
            workflows[wf_name] = chain

        return CompiledArtifact(
            handle=SemanticKernelHandle(workflows), diagnostics=diagnostics, intent=intent
        )

    async def run(self, artifact: CompiledArtifact, workflow: str, input_: str) -> AdapterResult:
        handle: SemanticKernelHandle = artifact.handle
        chain = handle.workflows.get(workflow)
        if chain is None:
            raise UnknownWorkflowError(f"Unknown workflow: {workflow!r}")

        current_input = input_
        trace: list[str] = []
        for sk_agent in chain:
            response = await sk_agent.get_response(messages=current_input)
            current_input = str(response.message.content)
            trace.append(sk_agent.name)

        return AdapterResult(
            output=current_input,
            raw=trace,
            usage={"agents_executed": len(trace)},
        )
