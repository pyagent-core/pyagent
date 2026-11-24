"""Tests for downward-only delegation, chain integrity, and revocation that cascades."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from pyagent_dns.authority import (
    CHAIN_BROKEN,
    Action,
    AttenuationError,
    AuthorityGraph,
    CallContext,
    DelegationTerms,
    Grant,
    GrantEffect,
    GrantScope,
    Limits,
    ResourceSelector,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyagent_dns.authority import Decision

EXPIRY = datetime(2028, 1, 1, tzinfo=UTC)


@pytest.fixture
def parent(delegable: Callable[..., Grant]) -> Grant:
    """A grant with every dimension bounded, so every kind of widening is possible."""
    return delegable(
        "parent",
        must_attenuate=True,
        resource=ResourceSelector(("internal", "public"), "tier_1", "portfolio-data.reader"),
        limits=Limits(
            max_records_per_call=500, max_calls_per_session=10, max_amount=1000.0, currency="USD"
        ),
        effect=GrantEffect.REQUIRE_APPROVAL,
        approver_role="compliance_officer",
        expires=EXPIRY,
    )


@pytest.fixture
def delegating(parent: Grant) -> AuthorityGraph:
    graph = AuthorityGraph()
    graph.add_grant(parent)
    return graph


def check(
    graph: AuthorityGraph, chain: list[str], resource: ResourceSelector | None = None
) -> Decision:
    return graph.authorize(
        chain,
        Action.CALL,
        "portfolio-data.reader",
        resource or ResourceSelector(account_scope="tier_1", name_scope="portfolio-data.reader"),
        CallContext("portfolio_review", request_payload=b"{}"),
    )


# -- Narrowing is accepted, widening is refused ----------------------------------------------


def test_narrowing_produces_a_child_that_inherits_the_rest(
    delegating: AuthorityGraph, parent: Grant
) -> None:
    result = delegating.delegate(
        "parent",
        delegate_principal="worker",
        scope=GrantScope(
            resource=ResourceSelector(("internal",)),
            limits=Limits(max_records_per_call=200),
            expires=datetime(2027, 1, 1, tzinfo=UTC),
        ),
    )
    child = result.grant
    assert child.principal == "worker"
    assert child.parent_grant_id == "parent"
    assert (child.action, child.capability, child.purpose) == (
        parent.action,
        parent.capability,
        parent.purpose,
    )
    assert child.resource.data_classes == ("internal",)
    assert child.resource.account_scope == "tier_1"  # inherited
    assert child.limits.max_records_per_call == 200
    assert child.limits.max_calls_per_session == 10  # inherited
    assert child.limits.currency == "USD"
    assert child.effect == GrantEffect.REQUIRE_APPROVAL  # delegation never weakens the effect
    assert child.approver_role == "compliance_officer"
    assert result.token.grant_chain == ("parent", child.grant_id)
    assert result.token.principal_chain == ("lead", "worker")
    assert result.token.effective_limits.max_records_per_call == 200
    assert result.token.token_hash.startswith("sha256:")


@pytest.mark.parametrize(
    ("dimension", "scope"),
    [
        (
            "resource.data_classes",
            GrantScope(resource=ResourceSelector(("internal", "confidential"))),
        ),
        (
            "resource.account_scope",
            GrantScope(resource=ResourceSelector(account_scope="all_accounts")),
        ),
        ("resource.name_scope", GrantScope(resource=ResourceSelector(name_scope="another-tool"))),
        ("purpose", GrantScope(purpose="marketing_campaign")),
        ("limits.max_records_per_call", GrantScope(limits=Limits(max_records_per_call=501))),
        ("limits.max_calls_per_session", GrantScope(limits=Limits(max_calls_per_session=11))),
        ("limits.max_amount", GrantScope(limits=Limits(max_amount=1000.01))),
        ("limits.currency", GrantScope(limits=Limits(currency="EUR"))),
        ("expires", GrantScope(expires=datetime(2035, 1, 1, tzinfo=UTC))),
    ],
)
def test_widening_any_dimension_is_refused_and_named(
    delegating: AuthorityGraph, dimension: str, scope: GrantScope
) -> None:
    with pytest.raises(AttenuationError) as exc_info:
        delegating.delegate("parent", delegate_principal="sub", scope=scope)
    assert exc_info.value.dimension == dimension


def test_a_lower_data_class_is_a_narrowing_even_if_the_parent_never_listed_it(
    delegable: Callable[..., Grant],
) -> None:
    graph = AuthorityGraph()
    graph.add_grant(delegable("p", resource=ResourceSelector(("internal",))))
    result = graph.delegate(
        "p", delegate_principal="w", scope=GrantScope(resource=ResourceSelector(("public",)))
    )
    assert result.grant.resource.data_classes == ("public",)


def test_a_parent_that_does_not_allow_delegation_refuses_it(
    delegable: Callable[..., Grant],
) -> None:
    graph = AuthorityGraph()
    graph.add_grant(delegable("p", delegation=DelegationTerms(allowed=False)))
    with pytest.raises(AttenuationError) as exc_info:
        graph.delegate("p", delegate_principal="w", scope=GrantScope())
    assert exc_info.value.dimension == "delegation.allowed"


def test_capability_and_action_cannot_change_through_delegation(
    delegable: Callable[..., Grant],
) -> None:
    graph = AuthorityGraph()
    parent = delegable("p")
    graph.add_grant(parent)
    for field, value in (("capability", "other.tool"), ("action", Action.DELETE)):
        illegal = Grant(
            grant_id=f"c_{field}",
            principal="w",
            parent_grant_id="p",
            **{**_fields(parent), field: value},
        )
        with pytest.raises(AttenuationError) as exc_info:
            graph.add_grant(illegal)
        assert exc_info.value.dimension == field


def _fields(grant: Grant) -> dict[str, Any]:
    return {
        "action": grant.action,
        "capability": grant.capability,
        "resource": grant.resource,
        "purpose": grant.purpose,
        "limits": grant.limits,
        "delegation": grant.delegation,
        "effect": grant.effect,
    }


# -- must_attenuate: a ceiling, and optionally a requirement to narrow ------------------------


def test_must_attenuate_refuses_a_delegate_that_narrows_nothing(
    delegable: Callable[..., Grant],
) -> None:
    graph = AuthorityGraph()
    graph.add_grant(delegable("p", must_attenuate=True))
    with pytest.raises(AttenuationError) as exc_info:
        graph.delegate("p", delegate_principal="w", scope=GrantScope())
    assert exc_info.value.dimension == "must_attenuate"


def test_must_attenuate_is_satisfied_by_narrowing_any_one_dimension(
    delegable: Callable[..., Grant],
) -> None:
    graph = AuthorityGraph()
    graph.add_grant(delegable("p", must_attenuate=True, limits=Limits(max_records_per_call=100)))
    result = graph.delegate(
        "p", delegate_principal="w", scope=GrantScope(limits=Limits(max_records_per_call=99))
    )
    assert result.grant.limits.max_records_per_call == 99


def test_without_must_attenuate_a_delegate_may_equal_the_parent_but_never_exceed_it(
    delegable: Callable[..., Grant],
) -> None:
    graph = AuthorityGraph()
    graph.add_grant(delegable("p", must_attenuate=False, limits=Limits(max_records_per_call=100)))
    assert graph.delegate("p", delegate_principal="w", scope=GrantScope()).grant.principal == "w"
    with pytest.raises(AttenuationError, match="max_records_per_call"):
        graph.delegate(
            "p", delegate_principal="x", scope=GrantScope(limits=Limits(max_records_per_call=101))
        )


def test_delegation_from_a_missing_revoked_or_expired_parent_is_refused(
    delegable: Callable[..., Grant],
) -> None:
    graph = AuthorityGraph(clock=lambda: datetime(2030, 1, 1, tzinfo=UTC).timestamp())
    graph.add_grants(
        [delegable("live"), delegable("old", expires=datetime(2029, 1, 1, tzinfo=UTC))]
    )
    graph.revoke("live")
    with pytest.raises(ValueError, match="not found"):
        graph.delegate("nope", delegate_principal="w", scope=GrantScope())
    for grant_id in ("live", "old"):
        with pytest.raises(ValueError, match="revoked or expired"):
            graph.delegate(grant_id, delegate_principal="w", scope=GrantScope())


# -- Chains ----------------------------------------------------------------------------------


@pytest.fixture
def three_hops(delegable: Callable[..., Grant]) -> AuthorityGraph:
    """lead -> manager -> worker, each hop narrowing the record cap."""
    graph = AuthorityGraph()
    graph.add_grant(delegable("g_lead", limits=Limits(max_records_per_call=300)))
    graph.delegate(
        "g_lead",
        delegate_principal="manager",
        scope=GrantScope(limits=Limits(max_records_per_call=200)),
    )
    return graph


def test_a_multi_hop_token_lists_the_whole_chain_root_first(three_hops: AuthorityGraph) -> None:
    manager_grant = three_hops.grants_for("manager")[0]
    result = three_hops.delegate(
        manager_grant.grant_id,
        delegate_principal="worker",
        scope=GrantScope(limits=Limits(max_records_per_call=50)),
    )
    assert result.token.principal_chain == ("lead", "manager", "worker")
    assert result.token.grant_chain == ("g_lead", manager_grant.grant_id, result.grant.grant_id)
    assert result.token.effective_limits.max_records_per_call == 50


def test_effective_limit_is_the_tightest_along_the_chain(three_hops: AuthorityGraph) -> None:
    limits = three_hops.effective_limit(
        ["lead", "manager"], Action.CALL, "portfolio-data.reader", ResourceSelector()
    )
    assert limits is not None
    assert limits.max_records_per_call == 200


def test_a_delegated_call_is_authorized_with_the_correct_chain(
    delegating: AuthorityGraph,
) -> None:
    delegating.delegate(
        "parent",
        delegate_principal="worker",
        scope=GrantScope(limits=Limits(max_records_per_call=100)),
    )
    decision = check(delegating, ["lead", "worker"])
    assert decision.outcome.value == "require_approval"  # the effect was inherited
    assert decision.grant_path[0] == "parent"
    assert len(decision.grant_path) == 2


def test_a_forged_delegator_in_the_principal_chain_is_rejected(
    delegating: AuthorityGraph,
) -> None:
    """The caller supplies the chain; naming a root the grant did not come from must not work."""
    delegating.delegate(
        "parent",
        delegate_principal="worker",
        scope=GrantScope(limits=Limits(max_records_per_call=1)),
    )
    decision = check(delegating, ["ceo", "worker"])
    assert decision.reason_code == CHAIN_BROKEN
    assert "does not match" in decision.reason


def test_a_chain_that_skips_or_adds_a_hop_is_rejected(three_hops: AuthorityGraph) -> None:
    worker = three_hops.delegate(
        three_hops.grants_for("manager")[0].grant_id,
        delegate_principal="worker",
        scope=GrantScope(limits=Limits(max_records_per_call=10)),
    )
    assert worker.grant.principal == "worker"

    def attempt(chain: list[str]) -> Decision:
        return three_hops.authorize(
            chain,
            Action.CALL,
            "portfolio-data.reader",
            ResourceSelector(),
            CallContext("portfolio_review"),
        )

    assert attempt(["lead", "manager", "worker"]).allowed
    assert attempt(["lead", "worker"]).reason_code == CHAIN_BROKEN
    assert attempt(["lead", "manager", "intern", "worker"]).reason_code == CHAIN_BROKEN


def test_a_call_with_no_chain_for_a_delegated_grant_is_still_checked_against_its_ancestors(
    delegating: AuthorityGraph,
) -> None:
    """Passing a one-element chain must not let a delegate outlive its revoked parent."""
    delegating.delegate(
        "parent",
        delegate_principal="worker",
        scope=GrantScope(limits=Limits(max_records_per_call=1)),
    )
    assert check(delegating, ["worker"]).outcome.value == "require_approval"
    delegating.revoke("parent")
    decision = check(delegating, ["worker"])
    assert decision.reason_code == CHAIN_BROKEN
    assert not decision.allowed


def test_revoking_the_parent_breaks_the_child_chain(delegating: AuthorityGraph) -> None:
    delegating.delegate(
        "parent",
        delegate_principal="worker",
        scope=GrantScope(limits=Limits(max_records_per_call=1)),
    )
    assert check(delegating, ["lead", "worker"]).outcome.value == "require_approval"
    delegating.revoke("parent")
    assert check(delegating, ["lead", "worker"]).reason_code == CHAIN_BROKEN


def test_reachable_leaves_out_grants_whose_chain_is_broken(delegating: AuthorityGraph) -> None:
    delegating.delegate(
        "parent",
        delegate_principal="worker",
        scope=GrantScope(limits=Limits(max_records_per_call=1)),
    )
    assert delegating.reachable("worker") == ["portfolio-data.reader"]
    delegating.revoke("parent")
    assert delegating.reachable("worker") == []


# -- The graph never holds a grant wider than its parent ---------------------------------------


def test_a_grant_loaded_with_a_parent_must_not_exceed_that_parent(
    delegable: Callable[..., Grant],
) -> None:
    """Attenuation is enforced on every path into the graph, not only through delegate()."""
    graph = AuthorityGraph()
    graph.add_grant(delegable("p", limits=Limits(max_records_per_call=100)))
    too_wide = Grant(
        grant_id="c",
        principal="w",
        action=Action.CALL,
        capability="portfolio-data.reader",
        resource=ResourceSelector(("restricted",)),
        purpose="portfolio_review",
        limits=Limits(max_records_per_call=100),
        parent_grant_id="p",
    )
    with pytest.raises(AttenuationError) as exc_info:
        graph.add_grant(too_wide)
    assert exc_info.value.dimension == "resource.data_classes"
    assert graph.get_grant("c") is None


def test_a_loaded_child_cannot_drop_a_bound_the_parent_set(delegable: Callable[..., Grant]) -> None:
    graph = AuthorityGraph()
    graph.add_grant(delegable("p", limits=Limits(max_records_per_call=100)))
    unbounded = Grant(
        grant_id="c",
        principal="w",
        action=Action.CALL,
        capability="portfolio-data.reader",
        resource=ResourceSelector(("internal",)),
        purpose="portfolio_review",
        parent_grant_id="p",
    )
    with pytest.raises(AttenuationError, match="max_records_per_call"):
        graph.add_grant(unbounded)


def test_a_grant_cannot_name_a_parent_that_is_not_in_the_graph(
    delegable: Callable[..., Grant],
) -> None:
    with pytest.raises(ValueError, match="not in the graph"):
        AuthorityGraph().add_grant(delegable("c", parent_grant_id="ghost"))


def test_a_duplicate_grant_id_is_refused(delegable: Callable[..., Grant]) -> None:
    graph = AuthorityGraph()
    graph.add_grant(delegable("p"))
    with pytest.raises(ValueError, match="already in the graph"):
        graph.add_grant(delegable("p", principal="someone_with_more_authority"))


def test_add_grants_accepts_children_before_parents(delegable: Callable[..., Grant]) -> None:
    graph = AuthorityGraph()
    child = delegable(
        "c", principal="w", parent_grant_id="p", limits=Limits(max_records_per_call=5)
    )
    parent = delegable("p", limits=Limits(max_records_per_call=10))
    graph.add_grants([child, parent])
    assert {g.grant_id for g in graph.grants_for("w")} == {"c"}


def test_add_grants_is_all_or_nothing(delegable: Callable[..., Grant]) -> None:
    graph = AuthorityGraph()
    good = delegable("good")
    bad = delegable("bad", parent_grant_id="ghost")
    with pytest.raises(ValueError, match="not in the graph"):
        graph.add_grants([good, bad])
    assert graph.get_grant("good") is None
