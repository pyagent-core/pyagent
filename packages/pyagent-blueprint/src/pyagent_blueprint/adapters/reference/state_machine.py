"""StateMachineAdapter: explicit finite-state-machine execution model.

Workflow = states (one per agent) + transitions (implicit linear order
unless `config.transitions` overrides it) + a trigger step function.
This is a different mental model than both `SequentialChainAdapter`
(pure data pipeline) and `PyAgentAdapter` (composed Pattern DAG) — a
state machine reasons about "what state am I in and what triggers a
move," not "what's the next stage in a chain" (see
TRANSFORMATION-PLAN.md Section 6).

Declares `Capability.PARTIAL_WORKFLOW_RUN` since a state machine can
naturally start from any declared state, not just the first.
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


class StateMachine:
    """A single workflow's compiled state machine.

    Attributes:
        states: Ordered list of state names (one per agent, by
            convention: ``f"{agent_name}_state"``).
        agent_by_state: state name -> (agent_name, prompt).
        transitions: state name -> next state name (``None`` at the
            terminal state).
    """

    def __init__(
        self,
        states: list[str],
        agent_by_state: dict[str, tuple[str, str]],
        transitions: dict[str, str | None],
    ) -> None:
        self.states = states
        self.agent_by_state = agent_by_state
        self.transitions = transitions

    @property
    def initial_state(self) -> str | None:
        return self.states[0] if self.states else None


class StateMachineHandle:
    def __init__(self, machines: dict[str, StateMachine]) -> None:
        self.machines = machines


class StateMachineAdapter(RuntimeAdapter):
    """Explicit FSM: states + triggers, not a graph or a chain."""

    name = "state_machine"
    capabilities = Capability.PARTIAL_WORKFLOW_RUN

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        diagnostics = diagnose_common_governance(ir)
        intent: dict[str, str] = {}
        machines: dict[str, StateMachine] = {}

        for wf_name, wf in ir.workflows.items():
            intent[wf_name] = wf.pattern
            ordered_refs = flatten_agent_refs(wf.agents)

            states: list[str] = []
            agent_by_state: dict[str, tuple[str, str]] = {}
            for agent_name in ordered_refs:
                state_name = f"{agent_name}_state"
                states.append(state_name)
                agent_ir = ir.agents.get(agent_name)
                agent_by_state[state_name] = (agent_name, agent_ir.prompt if agent_ir else "")

            transitions: dict[str, str | None] = {}
            for i, state in enumerate(states):
                transitions[state] = states[i + 1] if i + 1 < len(states) else None

            machines[wf_name] = StateMachine(states, agent_by_state, transitions)

        return CompiledArtifact(
            handle=StateMachineHandle(machines), diagnostics=diagnostics, intent=intent
        )

    async def run(
        self,
        compiled: CompiledArtifact,
        workflow: str,
        input_: str,
        *,
        start_state: str | None = None,
        **kwargs: Any,
    ) -> AdapterResult:
        handle: StateMachineHandle = compiled.handle
        if workflow not in handle.machines:
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow}'. Available: {list(handle.machines)}"
            )

        machine = handle.machines[workflow]
        current_state = start_state or machine.initial_state
        visited: list[str] = []
        current_input = input_

        while current_state is not None:
            agent_name, prompt = machine.agent_by_state[current_state]
            current_input = mock_call(agent_name, prompt, current_input)
            visited.append(current_state)
            current_state = machine.transitions.get(current_state)

        return AdapterResult(output=current_input, raw={"visited_states": visited})

    def supported_patterns(self) -> list[str]:
        return []
