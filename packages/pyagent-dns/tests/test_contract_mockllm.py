"""Contract tests: a Supervisor, a ReAct specialist, and guarded tools, driven only by MockLLM.

These assert shape, not model quality. What they pin down is the contract that matters most:
nothing runs without a decision, every decision is announced, and a denial reaches the model as
something it can act on. No test here touches the network or a provider.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pyagent_dns.authority import Action, AuthorityGraph, Grant, ResourceSelector
from pyagent_dns.middleware import AuthorizationDeniedError, DnsMiddleware
from pyagent_dns.records import RecordKind
from pyagent_patterns.advanced.react import ReAct
from pyagent_patterns.base import Agent, Message, MockLLM
from pyagent_patterns.orchestration.supervisor import Supervisor

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyagent_dns.records import NameRecord
    from pyagent_dns.registry import NameRegistry
    from pyagent_dns.resolver import Resolver

PURPOSE = "portfolio_review"


class ReActSpecialist(Agent):
    """An agent whose reply is the output of a ReAct loop over its guarded tools."""

    def __init__(self, name: str, llm: MockLLM, tools: dict[str, Callable[[str], str]]) -> None:
        super().__init__(name=name, llm=llm)
        self.react = ReAct(Agent(name, llm), tools, max_steps=5)
        self.tools_used: list[str] = []

    async def run(self, messages: list[Message]) -> Message:
        result = await self.react.run(messages[-1].content)
        self.tools_used = list(result.metadata["tools_used"])
        return Message.assistant(result.output)


class System:
    """The assembled system plus the probes the assertions read."""

    def __init__(self, resolver: Resolver, graph: AuthorityGraph, bus: Any) -> None:
        self.events: list[Any] = []
        bus.subscribe(self.events.append)
        self.middleware = DnsMiddleware(resolver, graph, event_bus=bus)
        self.vault_calls: list[str] = []
        self.positions_calls: list[str] = []
        self.worker_llm = MockLLM(
            [
                "Thought: the vault might have it.\nAction: client-vault-reader(dump)\n",
                "Thought: refused, use positions.\nAction: portfolio-data.reader(positions)\n",
                "Thought: enough.\nFINISH: The portfolio holds AAPL and MSFT.",
            ]
        )
        self.classifier_llm = MockLLM(["research"])
        tools = self.middleware.guard_tools(
            {
                "client-vault-reader": lambda q: (self.vault_calls.append(q), "SSN 123-45-6789")[1],
                "portfolio-data.reader": lambda q: (
                    self.positions_calls.append(q),
                    "AAPL 100, MSFT 200",
                )[1],
            },
            principal_chain=["research_agent"],
            purpose=PURPOSE,
        )
        self.specialist = ReActSpecialist("research_agent", self.worker_llm, tools)
        self.supervisor = Supervisor(
            classifier=Agent("supervisor", self.classifier_llm),
            routes={
                "research": self.middleware.wrap_agent(
                    self.specialist, principal="supervisor", purpose=PURPOSE
                )
            },
        )

    def decision_events(self) -> list[Any]:
        return [e for e in self.events if e.event_type == "authority_decision"]


@pytest.fixture
def system(
    registry: NameRegistry,
    graph: AuthorityGraph,
    resolver: Resolver,
    make_record: Callable[..., NameRecord],
) -> System:
    pytest.importorskip("pyagent_trace")
    from pyagent_trace.events import TraceEventBus

    registry.register(
        make_record("research_agent", kind=RecordKind.AGENT, capabilities=("research",))
    )
    graph.add_grant(
        Grant(
            "g_handoff",
            "supervisor",
            Action.CALL,
            "research_agent",
            ResourceSelector(("internal",)),
            PURPOSE,
        )
    )
    return System(resolver, graph, TraceEventBus())


async def test_the_supervisor_run_finishes_with_output_after_a_denied_tool(system: System) -> None:
    result = await system.supervisor.run("Audit the portfolio positions")
    assert "AAPL and MSFT" in result.output


async def test_the_ungranted_tool_never_runs_and_the_granted_one_runs_once(system: System) -> None:
    await system.supervisor.run("Audit the portfolio positions")
    assert system.vault_calls == []
    assert system.positions_calls == ["positions"]


async def test_the_model_is_shown_the_structured_denial_and_never_the_secret(
    system: System,
) -> None:
    await system.supervisor.run("Audit the portfolio positions")
    after_denial = "\n".join(m.content for m in system.worker_llm.call_log[1])
    assert "Observation: DENIED [NO_GRANT]" in after_denial
    assert "123-45-6789" not in after_denial


async def test_the_model_call_counts_match_so_a_hidden_call_would_fail_here(
    system: System,
) -> None:
    await system.supervisor.run("Audit the portfolio positions")
    assert system.classifier_llm.call_count == 1
    assert system.worker_llm.call_count == 3  # one per ReAct step, none for authorization


async def test_every_tool_attempt_and_the_handoff_has_one_authority_decision_event(
    system: System,
) -> None:
    """No silent calls: attempts are counted independently of the events that announce them."""
    await system.supervisor.run("Audit the portfolio positions")

    handoffs = 1
    tool_attempts = system.specialist.tools_used
    assert tool_attempts == ["client-vault-reader", "portfolio-data.reader"]

    events = system.decision_events()
    assert len(events) == handoffs + len(tool_attempts) == len(system.middleware.decisions)
    assert [(e.payload["capability"], e.payload["reason_code"]) for e in events] == [
        ("research_agent", "GRANT_FOUND"),
        ("client-vault-reader", "NO_GRANT"),
        ("portfolio-data.reader", "GRANT_FOUND"),
    ]


async def test_each_event_names_the_exact_record_it_was_decided_against(
    system: System, resolver: Resolver
) -> None:
    await system.supervisor.run("Audit the portfolio positions")
    for event in system.decision_events():
        resolution = resolver.resolve(event.payload["capability"])
        assert resolution is not None
        assert event.payload["record_fingerprint"] == resolution.fingerprint
        assert event.payload["verification_status"] == "verified"


async def test_a_handoff_to_an_agent_nobody_granted_is_stopped_before_any_model_runs(
    registry: NameRegistry,
    graph: AuthorityGraph,
    resolver: Resolver,
    make_record: Callable[..., NameRecord],
) -> None:
    registry.register(make_record("research_agent", kind=RecordKind.AGENT))
    middleware = DnsMiddleware(resolver, graph)  # no grant for "supervisor" -> research_agent
    specialist_llm = MockLLM(["should never run"])
    supervisor = Supervisor(
        classifier=Agent("supervisor", MockLLM(["research"])),
        routes={
            "research": middleware.wrap_agent(
                Agent("research_agent", specialist_llm), principal="supervisor", purpose=PURPOSE
            )
        },
    )
    with pytest.raises(AuthorizationDeniedError) as exc_info:
        await supervisor.run("Audit the portfolio positions")
    assert exc_info.value.decision.reason_code == "NO_GRANT"
    assert specialist_llm.call_count == 0
