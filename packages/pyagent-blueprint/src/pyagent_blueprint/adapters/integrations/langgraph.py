"""LangGraphAdapter: a real (not stubbed) pyagent-blueprint RuntimeAdapter
targeting LangGraph's `StateGraph`.

Ships inside `pyagent-blueprint` behind the optional `langgraph` extra
(`pip install "pyagent-blueprint[langgraph]"`) rather than as a separate
package — only importable when `langgraph` itself is installed, and
`AdapterRegistry.discover()` skips it gracefully otherwise. Certified
against the shared `AdapterConformanceSuite`, the same acceptance bar a
third-party adapter author would have to pass.

Node bodies use a deterministic mock LLM call (no API key required) so
this adapter is fully testable without network access — the point is to
prove the `RuntimeAdapter` contract maps cleanly onto LangGraph's actual
graph-execution engine (nodes, edges, compiled `Runnable`, `.ainvoke`,
`.astream`), not to be a production LLM integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from langgraph.graph import END, START, StateGraph

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


class _GraphState(TypedDict):
    input: str
    output: str
    trace: list[str]


class LangGraphHandle:
    """Opaque compiled artifact: workflow name -> compiled LangGraph app."""

    def __init__(self, apps: dict[str, Any]) -> None:
        self.apps = apps


def _make_node(agent_name: str, prompt: str):
    def _node(state: _GraphState) -> _GraphState:
        result = mock_call(agent_name, prompt, state["output"] or state["input"])
        return {
            "input": state["input"],
            "output": result,
            "trace": [*state["trace"], agent_name],
        }

    return _node


class LangGraphAdapter(RuntimeAdapter):
    """Compiles each blueprint workflow into a real LangGraph `StateGraph`.

    Every agent referenced by a workflow becomes a node in a linear chain
    (agent-ref order, resolved via `flatten_agent_refs`) wired
    START -> agent_1 -> agent_2 -> ... -> END. This mirrors
    `SequentialChainAdapter`'s topology exactly but through LangGraph's
    real graph-compilation and execution engine, which is what makes this
    a meaningful proof point rather than a restatement of the reference
    adapter.
    """

    name = "langgraph"
    capabilities = Capability.STREAMING

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics = diagnose_common_governance(ir)
        intent: dict[str, str] = {}
        apps: dict[str, Any] = {}

        for wf_name, wf in ir.workflows.items():
            intent[wf_name] = wf.pattern
            refs = flatten_agent_refs(wf.agents)

            graph = StateGraph(_GraphState)
            prev_node_name = START
            for agent_name in refs:
                agent_ir = ir.agents.get(agent_name)
                prompt = agent_ir.prompt if agent_ir else ""
                graph.add_node(agent_name, _make_node(agent_name, prompt))
                graph.add_edge(prev_node_name, agent_name)
                prev_node_name = agent_name
            graph.add_edge(prev_node_name, END)

            apps[wf_name] = graph.compile()

        return CompiledArtifact(
            handle=LangGraphHandle(apps), diagnostics=diagnostics, intent=intent
        )

    async def run(self, artifact: CompiledArtifact, workflow: str, input_: str) -> AdapterResult:
        handle: LangGraphHandle = artifact.handle
        app = handle.apps.get(workflow)
        if app is None:
            raise UnknownWorkflowError(f"Unknown workflow: {workflow!r}")

        final_state: _GraphState = await app.ainvoke({"input": input_, "output": "", "trace": []})
        return AdapterResult(
            output=final_state["output"],
            raw=final_state,
            usage={"nodes_executed": len(final_state["trace"])},
        )

    async def stream(self, artifact: CompiledArtifact, workflow: str, input_: str):
        handle: LangGraphHandle = artifact.handle
        app = handle.apps.get(workflow)
        if app is None:
            raise UnknownWorkflowError(f"Unknown workflow: {workflow!r}")

        async for event in app.astream({"input": input_, "output": "", "trace": []}):
            for node_name, node_state in event.items():
                yield f"[{node_name}] {node_state['output']}"
