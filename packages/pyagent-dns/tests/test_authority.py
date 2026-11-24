"""Tests for AuthorityGraph.authorize: the golden allow and every forbidden trace.

Each denial test pins the reason code, because the code is how an operator learns which
check refused a call. The central claim of the package gets the most explicit test:
discovering a capability does not grant it.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest
from pyagent_dns.authority import (
    AMOUNT_LIMIT_EXCEEDED,
    APPROVAL_REQUIRED,
    DATA_CLASS_EXCEEDED,
    GRANT_EXPIRED,
    GRANT_FOUND,
    LIMIT_EXCEEDED,
    NO_GRANT,
    NO_RECORD,
    PURPOSE_MISMATCH,
    RECORD_EXPIRED,
    RECORD_REVOKED,
    RECORD_SIGNATURE_INVALID,
    RECORD_UNVERIFIED,
    SESSION_LIMIT_EXCEEDED,
    Action,
    AuthorityGraph,
    CallContext,
    Grant,
    Limits,
    Obligation,
    Outcome,
    ResourceSelector,
)
from pyagent_dns.records import RecordKind, RecordStatus
from pyagent_dns.signing import VerificationStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyagent_dns.authority import Decision
    from pyagent_dns.records import NameRecord
    from pyagent_dns.registry import NameRegistry
    from pyagent_dns.resolver import Resolver

    from .conftest import ControllableClock


def grant(grant_id: str = "g", **fields: Any) -> Grant:
    """A grant for ``analyst`` to CALL the portfolio reader for portfolio_review."""
    defaults: dict[str, Any] = {
        "principal": "analyst",
        "action": Action.CALL,
        "capability": "portfolio-data.reader",
        "resource": ResourceSelector(data_classes=("internal",)),
        "purpose": "portfolio_review",
    }
    return Grant(grant_id=grant_id, **(defaults | fields))


# -- The golden allow ------------------------------------------------------------------------


def test_golden_allow_carries_everything_a_decision_log_needs(
    ask: Callable[..., Decision], resolver: Resolver
) -> None:
    decision = ask(records_requested=100)
    resolution = resolver.resolve("portfolio-data.reader")
    assert resolution is not None

    assert decision.allowed
    assert decision.reason_code == GRANT_FOUND
    assert decision.grant_path == ("g_portfolio",)
    assert decision.policy_versions == ("v14",)
    assert decision.record_name == "portfolio-data.reader"
    assert decision.record_version == "3.2.1"
    assert decision.record_fingerprint == resolution.fingerprint
    assert decision.record_verification == VerificationStatus.VERIFIED
    assert decision.data_classes == ("internal",)
    assert decision.effective_limits == Limits(max_records_per_call=500, max_calls_per_session=20)
    # A session limit means the call must be counted, and a counted call is logged.
    assert decision.outcome == Outcome.ALLOW_WITH_OBLIGATIONS
    assert decision.obligations == (Obligation.LOG_DECISION, Obligation.COUNT_AGAINST_BUDGET)


def test_plain_allow_has_no_obligations(ask: Callable[..., Decision]) -> None:
    decision = ask("public-docs.reader", action=Action.READ)
    assert decision.outcome == Outcome.ALLOW
    assert decision.obligations == ()


def test_empty_principal_chain_is_denied(graph: AuthorityGraph) -> None:
    decision = graph.authorize([], Action.CALL, "x", ResourceSelector(), CallContext("p"))
    assert decision.reason_code == NO_GRANT
    assert not decision.allowed


# -- The resolved record ---------------------------------------------------------------------


def test_deny_signature_failure(
    ask: Callable[..., Decision], registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    registry.register(make_record("portfolio-data.reader", tamper=True))
    decision = ask()
    assert decision.reason_code == RECORD_SIGNATURE_INVALID
    assert decision.record_verification == VerificationStatus.FAILED


def test_deny_unverified_record_for_non_public_read(
    ask: Callable[..., Decision], registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    registry.register(make_record("portfolio-data.reader", sign=False))
    decision = ask()
    assert decision.reason_code == RECORD_UNVERIFIED
    assert decision.record_verification == VerificationStatus.UNVERIFIED


def test_allow_unverified_record_for_public_read_only(
    ask: Callable[..., Decision], registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    """The single exception to the UNVERIFIED rule, pinned so it cannot quietly widen."""
    registry.register(
        make_record("public-docs.reader", data_classes=("public",), capabilities=(), sign=False)
    )
    decision = ask("public-docs.reader", action=Action.READ)
    assert decision.outcome == Outcome.ALLOW
    assert decision.record_verification == VerificationStatus.UNVERIFIED


def test_unverified_exception_is_read_only(
    graph: AuthorityGraph,
    ask: Callable[..., Decision],
    registry: NameRegistry,
    make_record: Callable[..., NameRecord],
) -> None:
    registry.register(
        make_record("public-docs.reader", data_classes=("public",), capabilities=(), sign=False)
    )
    graph.add_grant(
        Grant(
            grant_id="g_call_public",
            principal="research_agent",
            action=Action.CALL,
            capability="public-docs.reader",
            resource=ResourceSelector(data_classes=("public",)),
            purpose="portfolio_review",
        )
    )
    assert ask("public-docs.reader", action=Action.CALL).reason_code == RECORD_UNVERIFIED


def test_unverified_record_cannot_be_read_by_claiming_data_is_public(
    ask: Callable[..., Decision], registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    """The record says it handles internal data. The caller saying 'public' does not change that."""
    registry.register(make_record("public-docs.reader", data_classes=("internal",), sign=False))
    decision = ask(
        "public-docs.reader",
        action=Action.READ,
        resource=ResourceSelector(data_classes=("public",)),
    )
    assert decision.reason_code == RECORD_UNVERIFIED


def test_deny_revoked_record_even_when_a_cached_resolution_exists(
    graph: AuthorityGraph, resolver: Resolver, registry: NameRegistry
) -> None:
    ctx = CallContext("portfolio_review")

    def attempt() -> Decision:
        return graph.authorize(
            ["research_agent"],
            Action.CALL,
            "portfolio-data.reader",
            ResourceSelector(),
            ctx,
            resolver.resolve("portfolio-data.reader"),  # the cached path, not resolve_fresh
        )

    assert attempt().allowed
    registry.revoke("portfolio-data.reader")
    decision = attempt()
    assert decision.reason_code == RECORD_REVOKED
    assert decision.record_verification == VerificationStatus.VERIFIED  # signature is still good


def test_deny_expired_record_once_the_clock_passes_its_expiry(
    ask: Callable[..., Decision],
    registry: NameRegistry,
    make_record: Callable[..., NameRecord],
    frozen_clock: ControllableClock,
) -> None:
    registry.register(
        make_record("portfolio-data.reader", expires=frozen_clock.now_utc() + timedelta(hours=1))
    )
    assert ask().allowed
    frozen_clock.advance(2 * 3600)
    assert ask().reason_code == RECORD_EXPIRED


def test_deprecated_record_still_authorizes_but_says_so(
    ask: Callable[..., Decision], registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    """Deprecation is a migration signal, not a withdrawal."""
    registry.register(make_record("portfolio-data.reader", status=RecordStatus.DEPRECATED))
    decision = ask()
    assert decision.allowed
    assert "deprecated" in decision.reason


def test_a_resolution_cannot_authorize_a_capability_its_record_does_not_declare(
    graph: AuthorityGraph, resolver: Resolver
) -> None:
    """A verified, harmless record's resolution must not vouch for a different capability."""
    decision = graph.authorize(
        ["research_agent"],
        Action.CALL,
        "portfolio-data.reader",
        ResourceSelector(),
        CallContext("portfolio_review"),
        resolver.resolve("public-docs.reader"),
    )
    assert decision.reason_code == NO_RECORD
    assert not decision.allowed


def test_a_grant_on_a_declared_capability_string_authorizes_calls_to_the_record(
    graph: AuthorityGraph, resolver: Resolver
) -> None:
    """Records declare capability strings for discovery; a grant may name one instead of the record."""
    graph.add_grant(grant("g_cap", capability="read_positions"))
    decision = graph.authorize(
        ["analyst"],
        Action.CALL,
        "read_positions",
        ResourceSelector(),
        CallContext("portfolio_review"),
        resolver.resolve("portfolio-data.reader"),
    )
    assert decision.allowed
    assert decision.grant_path == ("g_cap",)


# -- Grants ----------------------------------------------------------------------------------


def test_deny_discovered_but_ungranted_capability(
    ask: Callable[..., Decision], registry: NameRegistry
) -> None:
    """Central claim: a name that resolves, verifies, and is discoverable is still not permission."""
    found = registry.discover({"read_vault"})
    assert [r.name for r in found] == ["client-vault-reader"]

    decision = ask("client-vault-reader")
    assert decision.reason_code == NO_GRANT
    assert decision.record_verification == VerificationStatus.VERIFIED


def test_deny_purpose_mismatch(ask: Callable[..., Decision]) -> None:
    decision = ask(purpose="marketing_export")
    assert decision.reason_code == PURPOSE_MISMATCH
    assert "portfolio_review" in decision.reason


def test_deny_grant_covers_lower_data_class(ask: Callable[..., Decision]) -> None:
    decision = ask(resource=ResourceSelector(data_classes=("confidential",)))
    assert decision.reason_code == DATA_CLASS_EXCEEDED
    assert "confidential" in decision.reason


def test_a_grant_for_a_higher_class_covers_lower_ones(
    graph: AuthorityGraph, ask: Callable[..., Decision]
) -> None:
    graph.add_grant(
        grant("g_conf", principal="research_agent", resource=ResourceSelector(("confidential",)))
    )
    assert ask(resource=ResourceSelector(data_classes=("public",))).allowed


def test_record_data_classes_are_a_floor_the_caller_cannot_understate(
    graph: AuthorityGraph, ask: Callable[..., Decision]
) -> None:
    """The vault record is confidential. An internal-only grant must not reach it by the caller
    declaring no data class at all."""
    graph.add_grant(grant("g_vault", principal="research_agent", capability="client-vault-reader"))
    decision = ask("client-vault-reader", resource=ResourceSelector())
    assert decision.reason_code == DATA_CLASS_EXCEEDED
    assert "confidential" in decision.reason


def test_name_scope_is_taken_from_the_resolved_record_not_the_caller(
    graph: AuthorityGraph, resolver: Resolver
) -> None:
    graph.add_grant(
        grant(
            "g_scoped",
            capability="read_positions",
            resource=ResourceSelector(("internal",), None, "other-tool"),
        )
    )
    decision = graph.authorize(
        ["analyst"],
        Action.CALL,
        "read_positions",
        ResourceSelector(name_scope="other-tool"),  # the caller claims the scoped name
        CallContext("portfolio_review"),
        resolver.resolve("portfolio-data.reader"),  # but the record is a different one
    )
    assert not decision.allowed
    assert "scoped to name 'other-tool'" in decision.reason


def test_account_scope_must_match_exactly(graph: AuthorityGraph, resolver: Resolver) -> None:
    graph.add_grant(grant("g_acct", resource=ResourceSelector(("internal",), "acct-1")))

    def attempt(account: str | None) -> Decision:
        return graph.authorize(
            ["analyst"],
            Action.CALL,
            "portfolio-data.reader",
            ResourceSelector(account_scope=account),
            CallContext("portfolio_review"),
            resolver.resolve("portfolio-data.reader"),
        )

    assert attempt("acct-1").allowed
    assert not attempt("acct-2").allowed
    assert not attempt(None).allowed


def test_deny_after_grant_revocation(graph: AuthorityGraph, ask: Callable[..., Decision]) -> None:
    assert ask().allowed
    assert graph.revoke("g_portfolio")
    assert ask().reason_code == NO_GRANT  # from the caller's side, revoked == never issued
    assert not graph.revoke("g_portfolio")


def test_deny_expired_grant_once_the_clock_passes_its_expiry(
    graph: AuthorityGraph, resolver: Resolver, frozen_clock: ControllableClock
) -> None:
    graph.add_grant(grant("g_temp", expires=frozen_clock.now_utc() + timedelta(hours=1)))

    def attempt() -> Decision:
        return graph.authorize(
            ["analyst"],
            Action.CALL,
            "portfolio-data.reader",
            ResourceSelector(),
            CallContext("portfolio_review"),
            resolver.resolve("portfolio-data.reader"),
        )

    assert attempt().allowed
    frozen_clock.advance(2 * 3600)
    assert attempt().reason_code == GRANT_EXPIRED


def test_an_expired_grant_does_not_shadow_a_valid_one(
    graph: AuthorityGraph, resolver: Resolver, frozen_clock: ControllableClock
) -> None:
    """Policy v13 expired, policy v14 is live: the call must be allowed, whatever order they sit in."""
    graph.add_grants(
        [
            grant(
                "g_v13", policy_version="v13", expires=frozen_clock.now_utc() + timedelta(hours=1)
            ),
            grant("g_v14", policy_version="v14"),
        ]
    )
    frozen_clock.advance(2 * 3600)
    decision = graph.authorize(
        ["analyst"],
        Action.CALL,
        "portfolio-data.reader",
        ResourceSelector(),
        CallContext("portfolio_review"),
        resolver.resolve("portfolio-data.reader"),
    )
    assert decision.allowed
    assert decision.grant_path == ("g_v14",)


# -- Limits ----------------------------------------------------------------------------------


def test_deny_records_limit_exceeded(ask: Callable[..., Decision]) -> None:
    assert ask(records_requested=500).allowed
    decision = ask(records_requested=501)
    assert decision.reason_code == LIMIT_EXCEEDED
    assert decision.effective_limits is not None
    assert decision.effective_limits.max_records_per_call == 500


def test_deny_session_limit_exceeded(ask: Callable[..., Decision]) -> None:
    assert ask(calls_in_session=19).allowed
    assert ask(calls_in_session=20).reason_code == SESSION_LIMIT_EXCEEDED


@pytest.fixture
def spend_grant(graph: AuthorityGraph) -> Grant:
    g = grant(
        "g_spend",
        principal="research_agent",
        action=Action.SPEND,
        limits=Limits(max_amount=1000.0, currency="USD"),
    )
    graph.add_grant(g)
    return g


@pytest.mark.usefixtures("spend_grant")
def test_deny_amount_limit_exceeded(ask: Callable[..., Decision]) -> None:
    kwargs: dict[str, Any] = {"action": Action.SPEND, "currency": "USD"}
    assert ask(amount=1000.0, **kwargs).allowed
    assert ask(amount=1000.01, **kwargs).reason_code == AMOUNT_LIMIT_EXCEEDED


@pytest.mark.usefixtures("spend_grant")
def test_deny_amount_in_the_wrong_currency(ask: Callable[..., Decision]) -> None:
    decision = ask(action=Action.SPEND, amount=10.0, currency="EUR")
    assert decision.reason_code == AMOUNT_LIMIT_EXCEEDED
    assert "Currency mismatch" in decision.reason


@pytest.mark.usefixtures("spend_grant")
def test_a_spend_under_an_amount_limit_must_state_its_amount(ask: Callable[..., Decision]) -> None:
    """A limit that cannot be evaluated is not silently skipped for the one action it exists for."""
    decision = ask(action=Action.SPEND)
    assert decision.reason_code == AMOUNT_LIMIT_EXCEEDED
    assert "must state its amount" in decision.reason


def test_limits_come_from_the_grant_that_authorized_the_call(
    graph: AuthorityGraph, resolver: Resolver
) -> None:
    """Two grants for one capability differing by purpose: the cap that applies is the matching one's."""
    graph.add_grants(
        [
            grant("g_wide", purpose="audit", limits=Limits(max_records_per_call=1000)),
            grant("g_narrow", purpose="triage", limits=Limits(max_records_per_call=10)),
        ]
    )

    def attempt(purpose: str, records: int) -> Decision:
        return graph.authorize(
            ["analyst"],
            Action.CALL,
            "portfolio-data.reader",
            ResourceSelector(),
            CallContext(purpose, records_requested=records),
            resolver.resolve("portfolio-data.reader"),
        )

    assert attempt("audit", 500).allowed
    narrow = attempt("triage", 500)
    assert narrow.reason_code == LIMIT_EXCEEDED
    assert narrow.grant_path == ("g_narrow",)
    # effective_limit selects the same grant, so a notebook query matches what the gateway did.
    queried = graph.effective_limit(
        ["analyst"], Action.CALL, "portfolio-data.reader", ResourceSelector(), purpose="triage"
    )
    assert queried == Limits(max_records_per_call=10)


# -- Approval --------------------------------------------------------------------------------


def test_require_approval_binds_to_the_exact_request(ask: Callable[..., Decision]) -> None:
    payload = b'{"format": "csv", "account": "123"}'
    decision = ask(action=Action.EXPORT, request_payload=payload)
    assert decision.outcome == Outcome.REQUIRE_APPROVAL
    assert decision.approval_binding == f"sha256:{hashlib.sha256(payload).hexdigest()}"
    assert Obligation.REQUIRE_APPROVAL_BOUND_TO_HASH in decision.obligations
    assert not decision.allowed

    other = ask(action=Action.EXPORT, request_payload=payload + b" ")
    assert other.approval_binding != decision.approval_binding


def test_an_approval_that_cannot_be_bound_to_a_request_is_denied(
    ask: Callable[..., Decision],
) -> None:
    decision = ask(action=Action.EXPORT)
    assert decision.reason_code == APPROVAL_REQUIRED
    assert decision.outcome == Outcome.DENY
    assert decision.approval_binding is None


# -- Obligations -----------------------------------------------------------------------------


def test_calling_a_confidential_record_carries_the_redact_obligation(
    graph: AuthorityGraph, ask: Callable[..., Decision]
) -> None:
    graph.add_grant(
        grant(
            "g_vault",
            principal="research_agent",
            capability="client-vault-reader",
            resource=ResourceSelector(("confidential",)),
        )
    )
    decision = ask("client-vault-reader")
    assert decision.outcome == Outcome.ALLOW_WITH_OBLIGATIONS
    assert Obligation.REDACT in decision.obligations
    assert Obligation.LOG_DECISION in decision.obligations


def test_every_high_risk_decision_is_logged(
    graph: AuthorityGraph, ask: Callable[..., Decision]
) -> None:
    graph.add_grant(grant("g_write", principal="research_agent", action=Action.WRITE))
    decision = ask(action=Action.WRITE)
    assert decision.allowed
    assert Obligation.LOG_DECISION in decision.obligations


# -- Coverage and reachability ---------------------------------------------------------------


def test_uncovered_reports_exactly_the_ungranted_record(graph: AuthorityGraph) -> None:
    assert graph.uncovered() == ["client-vault-reader"]


def test_uncovered_counts_a_grant_on_any_declared_capability(graph: AuthorityGraph) -> None:
    graph.add_grant(grant("g_vault_cap", capability="read_vault"))
    assert graph.uncovered() == []


def test_uncovered_stops_counting_a_revoked_grant(graph: AuthorityGraph) -> None:
    graph.revoke("g_public")
    assert graph.uncovered() == ["client-vault-reader", "public-docs.reader"]


def test_uncovered_without_a_registry_refuses_rather_than_claim_nothing_is_uncovered() -> None:
    with pytest.raises(ValueError, match="without a bound registry"):
        AuthorityGraph().uncovered()


def test_reachable_lists_current_capabilities(graph: AuthorityGraph) -> None:
    assert graph.reachable("research_agent") == ["portfolio-data.reader", "public-docs.reader"]
    assert graph.reachable("research_agent", purpose="marketing") == []
    graph.revoke("g_public")
    assert graph.reachable("research_agent") == ["portfolio-data.reader"]


def test_discovery_and_resolution_alone_never_produce_an_allow(
    registry: NameRegistry, resolver: Resolver
) -> None:
    """A graph with no grants denies every record in the registry."""
    empty = AuthorityGraph(registry)
    for record in registry.discover():
        decision = empty.authorize(
            ["anyone"],
            Action.CALL,
            record.name,
            ResourceSelector(),
            CallContext("portfolio_review"),
            resolver.resolve(record.name),
        )
        assert decision.reason_code == NO_GRANT, record.name


def test_kind_is_not_authority(
    graph: AuthorityGraph, registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    """An agent record and a tool record are authorized the same way: by grants."""
    registry.register(make_record("lead-agent", kind=RecordKind.AGENT))
    assert graph.uncovered() == ["client-vault-reader", "lead-agent"]
