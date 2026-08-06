"""CrewAIAdapter: a real (not stubbed) pyagent-blueprint RuntimeAdapter
targeting CrewAI.

Third Step 4b "pyagent.org example adapter" (after LangGraph and the
OpenAI Agents SDK, per ecosystem-reach prioritization). Depends on the
real `crewai` package and self-certifies via `AdapterConformanceSuite`
in its own CI/test suite — never installed in `pyagent-blueprint` core.

CrewAI is role-based: agents are declared with a `role`/`goal`/`backstory`
and paired with `Task`s, executed by a `Crew`. This is a third
structurally distinct model — neither a declared graph (LangGraph) nor
handoff/turn-based (OpenAI Agents SDK) — which is exactly the kind of
additional dissimilar proof point the plan calls for.

To keep this adapter fully offline-testable (no API key / network
required), each `Agent` is bound to a deterministic `FakeLLM`
(`crewai.llms.base_llm.BaseLLM` subclass) that returns
`mock_call(...)`'s output — so the adapter exercises CrewAI's real
`Crew.kickoff()` execution path (agents, tasks, sequential process), not
a bypass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
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


class _FakeDeterministicLLM(BaseLLM):
    """A `BaseLLM` implementation with no network dependency.

    Returns `mock_call(agent_name, prompt, ...)`'s output directly,
    letting `Crew.kickoff()` run its real sequential-process execution
    path against a deterministic, offline-safe response.
    """

    _agent_name: str = ""
    _prompt: str = ""

    def call(
        self,
        messages: str | list[dict[str, Any]],
        tools: list[Any] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> str:
        text_input = messages if isinstance(messages, str) else messages[-1]["content"]
        return mock_call(self._agent_name, self._prompt, text_input)


def _make_llm(agent_name: str, prompt: str) -> _FakeDeterministicLLM:
    llm = _FakeDeterministicLLM(model=f"fake-{agent_name}")
    object.__setattr__(llm, "_agent_name", agent_name)
    object.__setattr__(llm, "_prompt", prompt)
    return llm


class CrewAIHandle:
    """Opaque compiled artifact: workflow name -> compiled Crew."""

    def __init__(self, crews: dict[str, Crew]) -> None:
        self.crews = crews


class CrewAIAdapter(RuntimeAdapter):
    """Compiles each blueprint workflow into a role-based CrewAI `Crew`.

    Every agent referenced by a workflow (agent-ref order, resolved via
    `flatten_agent_refs`) becomes one CrewAI `Agent` + one `Task`,
    executed via `Process.sequential` — CrewAI's built-in task-context
    chaining feeds each task's output into the next. This is the
    role-based equivalent of `SequentialChainAdapter`'s linear pipeline,
    executed through CrewAI's actual `Crew.kickoff()` engine.
    """

    name = "crewai"
    capabilities = Capability.NONE

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics = diagnose_common_governance(ir)
        intent: dict[str, str] = {}
        crews: dict[str, Crew] = {}

        for wf_name, wf in ir.workflows.items():
            intent[wf_name] = wf.pattern
            refs = flatten_agent_refs(wf.agents)

            crew_agents: list[Agent] = []
            crew_tasks: list[Task] = []
            for i, agent_name in enumerate(refs):
                agent_ir = ir.agents.get(agent_name)
                prompt = agent_ir.prompt if agent_ir else ""
                sdk_agent = Agent(
                    role=agent_name,
                    goal=prompt or f"Act as {agent_name}",
                    backstory=agent_ir.description if agent_ir else "",
                    llm=_make_llm(agent_name, prompt),
                )
                task = Task(
                    description="{input}"
                    if i == 0
                    else "Continue based on the previous step for: {input}",
                    expected_output="A response from this step of the workflow.",
                    agent=sdk_agent,
                )
                crew_agents.append(sdk_agent)
                crew_tasks.append(task)

            crews[wf_name] = Crew(agents=crew_agents, tasks=crew_tasks, process=Process.sequential)

        return CompiledArtifact(handle=CrewAIHandle(crews), diagnostics=diagnostics, intent=intent)

    async def run(self, artifact: CompiledArtifact, workflow: str, input_: str) -> AdapterResult:
        handle: CrewAIHandle = artifact.handle
        crew = handle.crews.get(workflow)
        if crew is None:
            raise UnknownWorkflowError(f"Unknown workflow: {workflow!r}")

        result = await crew.kickoff_async(inputs={"input": input_})
        return AdapterResult(
            output=result.raw,
            raw=result,
            usage={"tasks_executed": len(crew.tasks)},
        )
