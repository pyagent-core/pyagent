"""Tests for DnsMiddleware: the tool guard, the agent wrapper, obligations, and approvals.

The failure policy under test is the opposite of the host codebase's hooks: nothing in
authorization or obligation handling may be turned into a proceed. A denied tool is never
called, an obligation that cannot be honored denies, and only trace emission is best effort.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

import pytest
from pyagent_dns.authority import (
    Action,
    AuthorityGraph,
    CallContext,
    Decision,
    Grant,
    GrantEffect,
    Limits,
    Outcome,
    ResourceSelector,
)
from pyagent_dns.middleware import (
    AuthorizationDeniedError,
    DnsMiddleware,
    SessionCounter,
)
from pyagent_dns.records import RecordKind
from pyagent_patterns.advanced.react import ReAct
from pyagent_patterns.base import Agent, Message, MockLLM

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyagent_dns.records import NameRecord
    from pyagent_dns.registry import NameRegistry
    from pyagent_dns.resolver import Resolver

PURPOSE = "portfolio_review"
SECRET = "SSN 123-45-6789"


class Tool:
    """A tool that records how often it was really invoked."""

    def __init__(self, output: str = "ok") -> None:
        self.calls: list[str] = []
        self.output = output

    def __call__(self, text: str) -> str:
        self.calls.append(text)
        return self.output


@pytest.fixture
def middleware(resolver: Resolver, graph: AuthorityGraph) -> DnsMiddleware:
    return DnsMiddleware(resolver, graph)


def guard(
    mw: DnsMiddleware, tools: dict[str, Any], **kwargs: Any
) -> dict[str, Callable[[str], str]]:
    defaults: dict[str, Any] = {"principal_chain": ["research_agent"], "purpose": PURPOSE}
    return mw.guard_tools(tools, **(defaults | kwargs))


def grant_vault(graph: AuthorityGraph, **fields: Any) -> None:
    defaults: dict[str, Any] = {
        "grant_id": "g_vault",
        "principal": "research_agent",
        "action": Action.CALL,
        "capability": "client-vault-reader",
        "resource": ResourceSelector(("confidential",)),
        "purpose": PURPOSE,
    }
    graph.add_grant(Grant(**(defaults | fields)))


# -- The tool guard --------------------------------------------------------------------------


def test_an_allowed_call_runs_the_tool_once_and_returns_its_output(
    middleware: DnsMiddleware,
) -> None:
    tool = Tool("positions: AAPL")
    out = guard(middleware, {"portfolio-data.reader": tool})["portfolio-data.reader"]("holdings?")
    assert out == "positions: AAPL"
    assert tool.calls == ["holdings?"]
    (decision,) = middleware.decisions
    assert decision.allowed
    assert decision.capability == "portfolio-data.reader"


def test_a_discovered_but_ungranted_tool_is_never_invoked(middleware: DnsMiddleware) -> None:
    vault = Tool(SECRET)
    out = guard(middleware, {"client-vault-reader": vault})["client-vault-reader"]("dump")
    assert out.startswith("DENIED [NO_GRANT]")
    assert vault.calls == []
    assert SECRET not in out
    assert middleware.decisions[-1].outcome == Outcome.DENY


def test_a_tool_whose_name_is_not_a_record_is_denied_with_no_record(
    middleware: DnsMiddleware,
) -> None:
    """A tools dict whose keys drifted from the record names fails loudly, and closed."""
    typo = Tool()
    out = guard(middleware, {"portfolio-data.reeder": typo})["portfolio-data.reeder"]("x")
    assert out.startswith("DENIED [NO_RECORD]")
    assert typo.calls == []


def test_guard_tools_returns_a_new_dict_and_leaves_the_originals_alone(
    middleware: DnsMiddleware,
) -> None:
    tools = {"portfolio-data.reader": Tool()}
    guarded = guard(middleware, tools)
    assert guarded is not tools
    assert guarded.keys() == tools.keys()
    assert guarded["portfolio-data.reader"] is not tools["portfolio-data.reader"]


def test_a_tool_that_raises_propagates_the_error_and_still_counts_as_a_call(
    middleware: DnsMiddleware,
) -> None:
    def broken(_: str) -> str:
        raise RuntimeError("upstream is down")

    guarded = guard(middleware, {"portfolio-data.reader": broken}, session_id="s")
    with pytest.raises(RuntimeError, match="upstream is down"):
        guarded["portfolio-data.reader"]("x")
    assert middleware._sessions.count("s", "portfolio-data.reader") == 1


# -- Session limits --------------------------------------------------------------------------


@pytest.fixture
def two_call_graph(graph: AuthorityGraph) -> AuthorityGraph:
    graph.add_grant(
        Grant(
            "g_two",
            "worker",
            Action.CALL,
            "portfolio-data.reader",
            ResourceSelector(("internal",)),
            PURPOSE,
            Limits(max_calls_per_session=2),
        )
    )
    return graph


def test_the_session_limit_is_enforced_through_the_counter(
    resolver: Resolver, two_call_graph: AuthorityGraph
) -> None:
    mw = DnsMiddleware(resolver, two_call_graph)
    tool = Tool()
    call = guard(mw, {"portfolio-data.reader": tool}, principal_chain=["worker"])[
        "portfolio-data.reader"
    ]
    assert [call("a"), call("b")] == ["ok", "ok"]
    third = call("c")
    assert third.startswith("DENIED [SESSION_LIMIT_EXCEEDED]")
    assert tool.calls == ["a", "b"]
    # Denied attempts do not consume budget, so more of them leave the tool untouched.
    assert call("d").startswith("DENIED [SESSION_LIMIT_EXCEEDED]")
    assert tool.calls == ["a", "b"]


def test_each_guard_tools_call_gets_its_own_session_unless_one_is_given(
    resolver: Resolver, two_call_graph: AuthorityGraph
) -> None:
    mw = DnsMiddleware(resolver, two_call_graph)

    def spend(session_id: str | None) -> list[str]:
        call = guard(
            mw, {"portfolio-data.reader": Tool()}, principal_chain=["worker"], session_id=session_id
        )["portfolio-data.reader"]
        return [call("x"), call("x"), call("x")]

    first, second = spend(None), spend(None)
    # Each unnamed guard gets a fresh session: two full budgets, not one shared budget.
    assert first[:2] == second[:2] == ["ok", "ok"]
    assert first[2].startswith("DENIED") and second[2].startswith("DENIED")
    assert spend("shared")[:2] == ["ok", "ok"]
    assert spend("shared")[0].startswith("DENIED")  # same explicit session: the budget is shared


def test_session_counter_scopes_counts_by_session_and_capability() -> None:
    counter = SessionCounter()
    assert counter.count("s1", "a") == 0
    assert [counter.increment("s1", "a"), counter.increment("s1", "a")] == [1, 2]
    assert counter.increment("s1", "b") == 1
    assert counter.increment("s2", "a") == 1
    counter.reset("s1")
    assert (counter.count("s1", "a"), counter.count("s1", "b"), counter.count("s2", "a")) == (
        0,
        0,
        1,
    )
    counter.reset()
    assert counter.count("s2", "a") == 0


# -- The primary use case: a ReAct worker that is denied, replans, and finishes ---------------


async def test_a_react_worker_is_denied_a_tool_reads_the_reason_and_finishes_with_the_one_it_has(
    middleware: DnsMiddleware,
) -> None:
    vault, portfolio = Tool(SECRET), Tool("AAPL 100, MSFT 200")
    tools = guard(middleware, {"client-vault-reader": vault, "portfolio-data.reader": portfolio})
    llm = MockLLM(
        [
            "Thought: try the vault.\nAction: client-vault-reader(dump)\n",
            "Thought: that was refused, use the portfolio.\nAction: portfolio-data.reader(positions)\n",
            "Thought: done.\nFINISH: AAPL and MSFT.",
        ]
    )
    result = await ReAct(Agent("worker", llm), tools, max_steps=5).run("review the portfolio")

    assert "AAPL and MSFT" in result.output
    assert vault.calls == []
    assert portfolio.calls == ["positions"]
    assert result.metadata["tools_used"] == ["client-vault-reader", "portfolio-data.reader"]
    # The model really was shown the structured reason, so it could replan.
    second_prompt = "\n".join(m.content for m in llm.call_log[1])
    assert "Observation: DENIED [NO_GRANT]" in second_prompt
    assert SECRET not in second_prompt
    assert [(d.capability, d.reason_code) for d in middleware.decisions] == [
        ("client-vault-reader", "NO_GRANT"),
        ("portfolio-data.reader", "GRANT_FOUND"),
    ]
    assert llm.call_count == 3  # no hidden model call


# -- Redaction -------------------------------------------------------------------------------


@pytest.fixture
def redacting(resolver: Resolver, graph: AuthorityGraph) -> Callable[..., DnsMiddleware]:
    """A middleware with a ContextRedactor, built on demand so each test chooses its settings."""
    pytest.importorskip("pyagent_context")
    from pyagent_context.item import Sensitivity
    from pyagent_context.redaction import ContextRedactor

    def build(**redactor_kwargs: Any) -> DnsMiddleware:
        redactor = ContextRedactor(max_sensitivity=Sensitivity.INTERNAL, **redactor_kwargs)
        return DnsMiddleware(resolver, graph, redactor=redactor)

    return build


def test_confidential_output_is_redacted_when_a_redactor_is_wired(
    graph: AuthorityGraph, redacting: Callable[..., DnsMiddleware]
) -> None:
    grant_vault(graph)
    vault = Tool(SECRET)
    out = guard(redacting(), {"client-vault-reader": vault})["client-vault-reader"]("dump")
    assert out == "[REDACTED]"
    assert vault.calls == ["dump"]  # it ran; its output just never left


def test_a_call_needing_redaction_is_denied_before_running_when_no_redactor_is_wired(
    graph: AuthorityGraph, middleware: DnsMiddleware
) -> None:
    grant_vault(graph)
    vault = Tool(SECRET)
    out = guard(middleware, {"client-vault-reader": vault})["client-vault-reader"]("dump")
    assert out.startswith("DENIED [OBLIGATION_UNAVAILABLE]")
    assert vault.calls == []
    assert middleware.decisions[-1].reason_code == "OBLIGATION_UNAVAILABLE"
    assert middleware.decisions[-1].outcome == Outcome.DENY


def test_a_redactor_that_fails_withholds_the_output_instead_of_returning_it(
    graph: AuthorityGraph, resolver: Resolver
) -> None:
    """The fail-open to guard against: redaction raises, and the raw secret is returned anyway."""
    grant_vault(graph)

    class Exploding:
        def redact_item(self, item: object) -> object:
            raise RuntimeError("redactor blew up")

    mw = DnsMiddleware(resolver, graph, redactor=Exploding())
    out = guard(mw, {"client-vault-reader": Tool(SECRET)})["client-vault-reader"]("dump")
    assert out.startswith("DENIED [OBLIGATION_UNAVAILABLE]")
    assert "SSN" not in out
    assert "RuntimeError" in out
    assert mw.decisions[-1].outcome == Outcome.DENY


def test_redaction_uses_the_highest_data_class_the_decision_evaluated(
    graph: AuthorityGraph,
    registry: NameRegistry,
    make_record: Callable[..., NameRecord],
    redacting: Callable[..., DnsMiddleware],
) -> None:
    """A record spanning internal and confidential data is confidential. The first-listed class is not the level."""
    registry.register(
        make_record("mixed-reader", capabilities=(), data_classes=("internal", "confidential"))
    )
    grant_vault(graph, grant_id="g_mixed", capability="mixed-reader")
    out = guard(redacting(), {"mixed-reader": Tool(SECRET)})["mixed-reader"]("x")
    assert out == "[REDACTED]"


def test_a_redactor_that_excludes_leaves_an_empty_result(
    graph: AuthorityGraph, redacting: Callable[..., DnsMiddleware]
) -> None:
    grant_vault(graph)
    out = guard(redacting(exclude_above=True), {"client-vault-reader": Tool(SECRET)})[
        "client-vault-reader"
    ]("dump")
    assert out == ""


def test_internal_output_is_returned_unchanged_even_with_a_redactor(
    redacting: Callable[..., DnsMiddleware],
) -> None:
    out = guard(redacting(), {"portfolio-data.reader": Tool("positions")})["portfolio-data.reader"](
        "x"
    )
    assert out == "positions"


# -- Approval --------------------------------------------------------------------------------


def export_tool(mw: DnsMiddleware) -> tuple[Tool, Callable[[str], str]]:
    tool = Tool("exported")
    return tool, guard(mw, {"portfolio-data.reader": tool}, action=Action.EXPORT)[
        "portfolio-data.reader"
    ]


def test_an_approver_that_says_yes_lets_the_call_run_and_the_log_shows_what_was_approved(
    resolver: Resolver, graph: AuthorityGraph
) -> None:
    seen: list[tuple[Decision, CallContext]] = []

    def approve(decision: Decision, context: CallContext) -> bool:
        seen.append((decision, context))
        return True

    mw = DnsMiddleware(resolver, graph, approver=approve)
    tool, export = export_tool(mw)
    assert export("csv please") == "exported"
    assert tool.calls == ["csv please"]

    digest = f"sha256:{hashlib.sha256(b'csv please').hexdigest()}"
    ((asked, context),) = seen
    assert asked.outcome == Outcome.REQUIRE_APPROVAL
    assert asked.approval_binding == digest
    assert context.request_payload == b"csv please"
    # The log holds the question and the final answer, both bound to the same request hash.
    pending, final = mw.decisions
    assert (pending.outcome, final.outcome) == (
        Outcome.REQUIRE_APPROVAL,
        Outcome.ALLOW_WITH_OBLIGATIONS,
    )
    assert final.approval_binding == digest


def test_an_approver_that_says_no_stops_the_call_and_the_refusal_is_logged(
    resolver: Resolver, graph: AuthorityGraph
) -> None:
    mw = DnsMiddleware(resolver, graph, approver=lambda d, c: False)
    tool, export = export_tool(mw)
    assert export("x").startswith("DENIED [APPROVAL_DENIED]")
    assert tool.calls == []
    assert [d.outcome for d in mw.decisions] == [Outcome.REQUIRE_APPROVAL, Outcome.DENY]
    assert mw.decisions[-1].reason_code == "APPROVAL_DENIED"


def test_with_no_approver_wired_an_approval_gated_call_is_denied_never_approved_by_default(
    middleware: DnsMiddleware,
) -> None:
    tool, export = export_tool(middleware)
    assert export("x").startswith("DENIED [APPROVAL_REQUIRED]")
    assert tool.calls == []
    assert middleware.decisions[-1].outcome == Outcome.DENY


def test_an_approval_covers_only_the_request_it_was_bound_to(
    resolver: Resolver, graph: AuthorityGraph
) -> None:
    bindings: list[str | None] = []
    mw = DnsMiddleware(
        resolver, graph, approver=lambda d, c: bindings.append(d.approval_binding) is None
    )
    _, export = export_tool(mw)
    export("request one")
    export("request two")
    assert len(set(bindings)) == 2


# -- Fresh resolution for high-risk actions --------------------------------------------------


def test_high_risk_actions_resolve_fresh_and_ordinary_ones_may_use_the_cache(
    resolver: Resolver, graph: AuthorityGraph, monkeypatch: pytest.MonkeyPatch
) -> None:
    routes: list[str] = []
    real_resolve, real_fresh = resolver.resolve, resolver.resolve_fresh
    monkeypatch.setattr(
        resolver, "resolve", lambda *a, **k: routes.append("cached") or real_resolve(*a, **k)
    )
    monkeypatch.setattr(
        resolver, "resolve_fresh", lambda *a, **k: routes.append("fresh") or real_fresh(*a, **k)
    )
    mw = DnsMiddleware(resolver, graph, approver=lambda d, c: True)

    guard(mw, {"portfolio-data.reader": Tool()})["portfolio-data.reader"]("x")
    export_tool(mw)[1]("x")
    assert routes == ["cached", "fresh"]


def test_revoking_a_record_between_two_calls_denies_the_second(
    middleware: DnsMiddleware, registry: NameRegistry
) -> None:
    tool = Tool()
    call = guard(middleware, {"portfolio-data.reader": tool})["portfolio-data.reader"]
    assert call("1") == "ok"
    registry.revoke("portfolio-data.reader")
    assert call("2").startswith("DENIED [RECORD_REVOKED]")
    assert tool.calls == ["1"]


# -- Events ----------------------------------------------------------------------------------


def test_every_guarded_call_emits_an_authority_decision_event_carrying_the_evidence(
    resolver: Resolver, graph: AuthorityGraph
) -> None:
    trace = pytest.importorskip("pyagent_trace.events")
    bus = trace.TraceEventBus()
    events: list[Any] = []
    bus.subscribe(events.append)
    mw = DnsMiddleware(resolver, graph, event_bus=bus)

    tools = guard(mw, {"portfolio-data.reader": Tool(), "client-vault-reader": Tool()})
    tools["portfolio-data.reader"]("a")
    tools["client-vault-reader"]("b")

    assert [e.event_type for e in events] == ["authority_decision"] * 2
    allow, deny = (e.payload for e in events)
    assert allow["reason_code"] == "GRANT_FOUND"
    assert allow["record_fingerprint"].startswith("sha256:")
    assert allow["record_version"] == "3.2.1"
    assert allow["verification_status"] == "verified"
    assert allow["grant_path"] == ["g_portfolio"]
    assert allow["policy_versions"] == ["v14"]
    assert deny["reason_code"] == "NO_GRANT"


def test_a_broken_event_bus_never_blocks_a_call(resolver: Resolver, graph: AuthorityGraph) -> None:
    pytest.importorskip("pyagent_trace")

    class Broken:
        def emit(self, event: object) -> None:
            raise RuntimeError("exporter down")

    mw = DnsMiddleware(resolver, graph, event_bus=Broken())
    tool = Tool()
    assert guard(mw, {"portfolio-data.reader": tool})["portfolio-data.reader"]("x") == "ok"
    assert len(mw.decisions) == 1


# -- authorize_call --------------------------------------------------------------------------


def test_authorize_call_is_the_entry_point_for_callers_with_their_own_gateway(
    middleware: DnsMiddleware,
) -> None:
    decision = middleware.authorize_call(
        principal_chain=["research_agent"],
        action=Action.CALL,
        capability="portfolio-data.reader",
        resource=ResourceSelector(),
        context=CallContext(PURPOSE, records_requested=501),
    )
    assert decision.reason_code == "LIMIT_EXCEEDED"  # facts a ReAct string cannot carry
    assert middleware.decisions == [decision]


def test_authorize_call_with_an_unknown_name_is_no_record_and_never_raises(
    middleware: DnsMiddleware,
) -> None:
    for chain in (["research_agent"], []):
        decision = middleware.authorize_call(
            principal_chain=chain,
            action=Action.CALL,
            capability="no-such-record",
            resource=ResourceSelector(),
            context=CallContext(PURPOSE),
        )
        assert decision.reason_code == "NO_RECORD"
    assert len(middleware.decisions) == 2


def test_the_decisions_property_is_a_copy(middleware: DnsMiddleware) -> None:
    middleware.decisions.append(None)  # type: ignore[arg-type]
    assert middleware.decisions == []


# -- Agent wrapper ---------------------------------------------------------------------------


@pytest.fixture
def agent_record(
    registry: NameRegistry, graph: AuthorityGraph, make_record: Callable[..., NameRecord]
) -> None:
    registry.register(
        make_record("analyst-agent", kind=RecordKind.AGENT, capabilities=("analyze",))
    )
    graph.add_grant(
        Grant(
            "g_agent",
            "research_agent",
            Action.CALL,
            "analyst-agent",
            ResourceSelector(("internal",)),
            PURPOSE,
        )
    )


async def test_a_denied_handoff_raises_with_the_decision_and_spends_no_model_call(
    middleware: DnsMiddleware,
) -> None:
    llm = MockLLM(["should never run"])
    stranger = middleware.wrap_agent(
        Agent("unknown-agent", llm), principal="research_agent", purpose=PURPOSE
    )
    with pytest.raises(AuthorizationDeniedError) as exc_info:
        await stranger.run([Message.user("hi")])
    assert exc_info.value.decision.reason_code == "NO_RECORD"
    assert llm.call_count == 0


@pytest.mark.usefixtures("agent_record")
async def test_an_allowed_handoff_runs_the_wrapped_agent_unchanged(
    middleware: DnsMiddleware,
) -> None:
    llm = MockLLM(["analysis complete"])
    wrapped = middleware.wrap_agent(
        Agent("analyst-agent", llm), principal="research_agent", purpose=PURPOSE
    )
    reply = await wrapped.run([Message.user("analyze")])
    assert reply.content == "analysis complete"
    assert llm.call_count == 1
    assert wrapped.name == "analyst-agent"


@pytest.mark.usefixtures("agent_record")
async def test_an_ungranted_principal_cannot_reach_a_known_agent(middleware: DnsMiddleware) -> None:
    llm = MockLLM(["x"])
    wrapped = middleware.wrap_agent(
        Agent("analyst-agent", llm), principal="intruder", purpose=PURPOSE
    )
    with pytest.raises(AuthorizationDeniedError) as exc_info:
        await wrapped.run([Message.user("hi")])
    assert exc_info.value.decision.reason_code == "NO_GRANT"
    assert llm.call_count == 0


@pytest.mark.usefixtures("agent_record")
async def test_wrap_all_wraps_each_agent_with_the_same_principal_and_purpose(
    middleware: DnsMiddleware,
) -> None:
    wrapped = middleware.wrap_all(
        [Agent("analyst-agent", MockLLM(["a"])), Agent("other", MockLLM(["b"]))],
        principal="research_agent",
        purpose=PURPOSE,
    )
    assert [w.name for w in wrapped] == ["analyst-agent", "other"]
    assert (await wrapped[0].run([Message.user("x")])).content == "a"
    with pytest.raises(AuthorizationDeniedError):
        await wrapped[1].run([Message.user("x")])


async def test_an_agent_handoff_gated_by_approval_is_refused_because_it_has_no_request_to_bind(
    graph: AuthorityGraph,
    registry: NameRegistry,
    resolver: Resolver,
    make_record: Callable[..., NameRecord],
) -> None:
    registry.register(make_record("gated-agent", kind=RecordKind.AGENT))
    graph.add_grant(
        Grant(
            "g_gated",
            "research_agent",
            Action.CALL,
            "gated-agent",
            ResourceSelector(("internal",)),
            PURPOSE,
            effect=GrantEffect.REQUIRE_APPROVAL,
        )
    )
    asked: list[Decision] = []
    mw = DnsMiddleware(resolver, graph, approver=lambda d, c: asked.append(d) is None)
    llm = MockLLM(["x"])
    gated = mw.wrap_agent(Agent("gated-agent", llm), principal="research_agent", purpose=PURPOSE)
    with pytest.raises(AuthorizationDeniedError) as exc_info:
        await gated.run([Message.user("x")])
    decision = exc_info.value.decision
    assert (decision.outcome, decision.reason_code) == (Outcome.DENY, "APPROVAL_REQUIRED")
    assert asked == []  # an approval cannot be bound to a request that was never hashed
    assert llm.call_count == 0


async def test_a_confidential_agent_reply_is_redacted_or_the_handoff_is_refused(
    graph: AuthorityGraph,
    registry: NameRegistry,
    resolver: Resolver,
    make_record: Callable[..., NameRecord],
    redacting: Callable[..., DnsMiddleware],
) -> None:
    registry.register(
        make_record("vault-agent", kind=RecordKind.AGENT, data_classes=("confidential",))
    )
    graph.add_grant(
        Grant(
            "g_va",
            "research_agent",
            Action.CALL,
            "vault-agent",
            ResourceSelector(("confidential",)),
            PURPOSE,
        )
    )
    redacted = (
        await redacting()
        .wrap_agent(
            Agent("vault-agent", MockLLM([SECRET])), principal="research_agent", purpose=PURPOSE
        )
        .run([Message.user("x")])
    )
    assert redacted.content == "[REDACTED]"

    llm = MockLLM([SECRET])
    unredactable = DnsMiddleware(resolver, graph).wrap_agent(
        Agent("vault-agent", llm), principal="research_agent", purpose=PURPOSE
    )
    with pytest.raises(AuthorizationDeniedError) as exc_info:
        await unredactable.run([Message.user("x")])
    assert exc_info.value.decision.reason_code == "OBLIGATION_UNAVAILABLE"
    assert llm.call_count == 0


@pytest.mark.usefixtures("agent_record")
async def test_authorization_wraps_routing_so_a_denied_call_costs_no_model_selection(
    middleware: DnsMiddleware,
) -> None:
    """Authorization outside, routing inside: the denied call never reaches the router."""
    router = pytest.importorskip("pyagent_router.middleware")
    routed_denied = router.RouterMiddleware({}).wrap(Agent("unknown-agent", MockLLM(["x"])))
    routed_allowed = router.RouterMiddleware({}).wrap(Agent("analyst-agent", MockLLM(["fine"])))

    with pytest.raises(AuthorizationDeniedError):
        await middleware.wrap_agent(routed_denied, principal="research_agent", purpose=PURPOSE).run(
            [Message.user("hi")]
        )
    assert routed_denied.routing_log == []

    reply = await middleware.wrap_agent(
        routed_allowed, principal="research_agent", purpose=PURPOSE
    ).run([Message.user("hi")])
    assert reply.content == "fine"
    assert len(routed_allowed.routing_log) == 1
