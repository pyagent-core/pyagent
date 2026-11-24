"""Seeded property tests for downward-only delegation.

The property that matters is about behavior, not fields: a delegate must never be able to do
anything its parent could not. So these tests build random child grants, let the graph accept or
refuse them, and compare what each accepted child is authorized to do with what its parent is.
No property-testing library is used: the repository has none, so a seeded ``random.Random``
keeps the test dependency-free and reproducible.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from pyagent_dns.authority import (
    Action,
    AttenuationError,
    AuthorityGraph,
    CallContext,
    DelegationTerms,
    Grant,
    GrantScope,
    Limits,
    ResourceSelector,
)

CLASSES = ("public", "internal", "confidential", "restricted")
CASES = 200
BASE = datetime(2026, 6, 1, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = BASE

    def __call__(self) -> float:
        return self.now.timestamp()


def random_parent(rng: random.Random) -> Grant:
    return Grant(
        grant_id="parent",
        principal="lead",
        action=Action.CALL,
        capability="data.service",
        resource=ResourceSelector(
            tuple(rng.sample(CLASSES, rng.randint(1, 4))), rng.choice([None, "a"]), None
        ),
        purpose="audit",
        limits=Limits(
            max_records_per_call=rng.randint(100, 1000),
            max_calls_per_session=rng.randint(5, 50),
            max_amount=float(rng.randint(500, 5000)),
            currency="USD",
        ),
        delegation=DelegationTerms(allowed=True, must_attenuate=False),
        expires=BASE + timedelta(days=rng.randint(10, 100)),
    )


def mode(rng: random.Random) -> str:
    """Each dimension of a child independently narrows, matches, or widens its parent."""
    return rng.choices(["narrow", "equal", "widen"], weights=[40, 45, 15])[0]


def random_child(rng: random.Random, parent: Grant) -> Grant:
    """A child built directly, so any dimension can widen, including by being left unbounded."""
    rank = max(CLASSES.index(c) for c in parent.resource.data_classes)
    kind = mode(rng)
    if kind == "widen" and rank < 3:
        classes = tuple(rng.sample(CLASSES, rng.randint(rank + 1, 4)))
        if max(CLASSES.index(c) for c in classes) <= rank:
            classes = (CLASSES[rank + 1],)
    elif kind == "narrow":
        classes = tuple(rng.sample(CLASSES[: rank + 1], rng.randint(1, rank + 1)))
    else:
        classes = parent.resource.data_classes

    def scope(parent_value: str | None) -> str | None:
        kind = mode(rng)
        if parent_value is None:  # nothing to widen past; narrowing is allowed
            return "a" if kind == "narrow" else None
        return {"narrow": parent_value, "equal": parent_value, "widen": rng.choice([None, "b"])}[
            kind
        ]

    def bound(parent_value: Any, spread: int) -> Any:
        return {
            "narrow": max(1, parent_value - rng.randint(1, spread)),
            "equal": parent_value,
            "widen": rng.choice([None, parent_value + rng.randint(1, spread)]),
        }[mode(rng)]

    p = parent.limits
    expiry = {
        "narrow": parent.expires - timedelta(days=rng.randint(1, 9)),
        "equal": parent.expires,
        "widen": rng.choice([None, parent.expires + timedelta(days=rng.randint(1, 9))]),
    }[mode(rng)]
    return Grant(
        grant_id="child",
        principal="worker",
        action=Action.CALL,
        capability="data.service",
        resource=ResourceSelector(classes, scope(parent.resource.account_scope), None),
        purpose="audit" if rng.random() < 0.92 else "marketing",
        limits=Limits(
            max_records_per_call=bound(p.max_records_per_call, 100),
            max_calls_per_session=bound(p.max_calls_per_session, 4),
            max_amount=bound(p.max_amount, 400),
            currency="USD" if rng.random() < 0.97 else "EUR",
        ),
        expires=expiry,
        parent_grant_id="parent",
    )


def random_call(rng: random.Random, parent: Grant) -> tuple[ResourceSelector, CallContext, int]:
    """A call, biased towards ones the parent would permit so the child's allows get tested."""
    rank = max(CLASSES.index(c) for c in parent.resource.data_classes)
    pool = CLASSES if rng.random() < 0.2 else CLASSES[: rank + 1]
    p = parent.limits
    assert p.max_records_per_call and p.max_calls_per_session and p.max_amount
    resource = ResourceSelector(
        tuple(rng.sample(pool, rng.randint(0, min(3, len(pool))))),
        rng.choice([None, parent.resource.account_scope, "b"]),
        None,
    )
    context = CallContext(
        purpose="audit" if rng.random() < 0.9 else "marketing",
        calls_in_session=rng.randint(0, int(p.max_calls_per_session * 1.15)),
        records_requested=rng.choice([None, rng.randint(1, int(p.max_records_per_call * 1.15))]),
        amount=rng.choice([None, float(rng.randint(1, int(p.max_amount * 1.15)))]),
        currency="USD",
    )
    assert parent.expires is not None
    return resource, context, rng.randint(0, (parent.expires - BASE).days + 5)


def allowed(
    graph: AuthorityGraph, chain: list[str], call: tuple[Any, Any, int], clock: Clock
) -> bool:
    resource, context, days = call
    clock.now = BASE + timedelta(days=days)
    return graph.authorize(chain, Action.CALL, "data.service", resource, context).allowed


def test_an_accepted_child_never_authorizes_more_than_its_parent() -> None:
    rng = random.Random(42)
    accepted = refused = child_allowed_calls = 0
    for _ in range(CASES):
        clock = Clock()
        graph = AuthorityGraph(clock=clock)
        parent = random_parent(rng)
        graph.add_grant(parent)
        child = random_child(rng, parent)
        try:
            graph.add_grant(child)
        except AttenuationError:
            refused += 1
            continue
        accepted += 1
        for _ in range(40):
            call = random_call(rng, parent)
            if allowed(graph, ["lead", "worker"], call, clock):
                child_allowed_calls += 1
                assert allowed(graph, ["lead"], call, clock), (parent, child, call)

    assert accepted >= 20, "too few children accepted for the property to mean anything"
    assert refused >= 20, "too few children refused: the refusal path was not exercised"
    assert child_allowed_calls >= 100, "the child allowed too few calls to test against the parent"


def test_delegate_never_hands_out_more_than_it_holds() -> None:
    rng = random.Random(7)
    accepted = refused = 0
    for _ in range(CASES):
        clock = Clock()
        graph = AuthorityGraph(clock=clock)
        parent = random_parent(rng)
        graph.add_grant(parent)
        scope = GrantScope(
            resource=ResourceSelector(tuple(rng.sample(CLASSES, rng.randint(1, 4)))),
            purpose="audit" if rng.random() < 0.9 else "marketing",
            limits=Limits(
                max_records_per_call=rng.choice([None, rng.randint(50, 1100)]),
                max_calls_per_session=rng.choice([None, rng.randint(1, 55)]),
            ),
            expires=rng.choice([None, parent.expires + timedelta(days=rng.randint(-20, 20))]),
        )
        try:
            result = graph.delegate("parent", delegate_principal="worker", scope=scope)
        except AttenuationError:
            refused += 1
            continue
        accepted += 1
        # Whatever the token says binds the delegate is no looser than the parent's own limits.
        bound = result.token.effective_limits
        assert (bound.max_records_per_call or 0) <= (parent.limits.max_records_per_call or 0)
        assert (bound.max_calls_per_session or 0) <= (parent.limits.max_calls_per_session or 0)
        for _ in range(40):
            call = random_call(rng, parent)
            if allowed(graph, ["lead", "worker"], call, clock):
                assert allowed(graph, ["lead"], call, clock), (parent, result.grant, call)

    assert accepted >= 20
    assert refused >= 20
