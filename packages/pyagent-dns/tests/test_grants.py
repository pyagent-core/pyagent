"""Tests for grant construction and loading.

A grant file is policy. A typo in it must not quietly produce a more permissive grant than the
author wrote, so these loaders reject what they do not recognize instead of defaulting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pyagent_dns.authority import (
    Action,
    Decision,
    DelegationTerms,
    Grant,
    GrantEffect,
    GrantLoadError,
    Limits,
    Outcome,
    ResourceSelector,
    load_grants_file,
)

FIXTURES = Path(__file__).parent / "fixtures"


def raw(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "grant_id": "g1",
        "principal": "research_agent",
        "action": "export",
        "capability": "portfolio-data.reader",
        "purpose": "portfolio_review",
        "resource": {"data_classes": ["confidential"]},
        "effect": "require_approval",
        "approver_role": "data_owner",
    }
    return base | overrides


def test_a_grant_loads_with_every_field_it_was_written_with() -> None:
    grant = Grant.from_dict(
        raw(
            limits={"max_records_per_call": 10, "max_amount": 5.5, "currency": "USD"},
            delegation={"allowed": True, "must_attenuate": False},
            granted_by="wealth_platform_policy",
            policy_version="v14",
            expires="2027-01-01T00:00:00Z",
            parent_grant_id=None,
        )
    )
    assert grant.action == Action.EXPORT
    assert grant.effect == GrantEffect.REQUIRE_APPROVAL
    assert grant.resource == ResourceSelector(("confidential",))
    assert grant.limits == Limits(max_records_per_call=10, max_amount=5.5, currency="USD")
    assert grant.delegation == DelegationTerms(allowed=True, must_attenuate=False)
    assert (grant.granted_by, grant.policy_version) == ("wealth_platform_policy", "v14")
    assert grant.expires == datetime(2027, 1, 1, tzinfo=UTC)


def test_a_grant_survives_a_dict_round_trip() -> None:
    grant = Grant.from_dict(
        raw(limits={"max_amount": 5.0, "currency": "USD"}, expires="2027-01-01T00:00:00Z")
    )
    assert Grant.from_dict(grant.to_dict()) == grant


def test_the_committed_fixture_grants_load() -> None:
    (grant,) = load_grants_file(FIXTURES / "grants.yaml")
    assert grant.grant_id == "grant_fixture_001"
    assert grant.policy_version == "v14"


@pytest.mark.parametrize("key", ["grant_id", "principal", "action", "capability", "purpose"])
def test_the_fields_that_decide_what_a_grant_means_are_required(key: str) -> None:
    data = raw()
    del data[key]
    with pytest.raises(GrantLoadError, match=f"missing required key.*{key}"):
        Grant.from_dict(data)


def test_a_misspelled_effect_does_not_quietly_become_allow() -> None:
    """`efect: require_approval` would otherwise load as an ordinary allow, failing open."""
    data = raw()
    del data["effect"]
    data["efect"] = "require_approval"
    with pytest.raises(GrantLoadError, match=r"unknown key.*efect"):
        Grant.from_dict(data)


def test_a_grant_with_no_stable_id_is_refused_rather_than_given_a_random_one() -> None:
    """A generated id differs on every load, so no delegation or decision log could name it."""
    data = raw()
    del data["grant_id"]
    with pytest.raises(GrantLoadError, match="grant_id"):
        Grant.from_dict(data)


@pytest.mark.parametrize("value", ["false", "true", "yes", 1, 0, None])
def test_delegation_flags_must_be_real_booleans(value: Any) -> None:
    """bool('false') is True: a quoted YAML value must not switch delegation on."""
    with pytest.raises(GrantLoadError, match="must be true or false"):
        Grant.from_dict(raw(delegation={"allowed": value}))


def test_delegation_defaults_are_closed() -> None:
    grant = Grant.from_dict(raw())
    assert grant.delegation == DelegationTerms(allowed=False, must_attenuate=True)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"action": "teleport"}, "teleport"),
        ({"effect": "maybe"}, "maybe"),
        ({"resource": {"data_classes": ["top_secret"]}}, "Unknown data class 'top_secret'"),
        ({"resource": {"data_classes": "internal"}}, "must be a list"),
        ({"resource": {"data_class": ["internal"]}}, "unknown key.*data_class"),
        ({"limits": {"max_records_per_call": -1}}, "non-negative"),
        ({"limits": {"max_records_per_call": "50"}}, "non-negative integer"),
        ({"limits": {"max_calls_per_session": True}}, "non-negative integer"),
        ({"limits": {"max_amount": -5, "currency": "USD"}}, "non-negative number"),
        ({"limits": {"max_amount": 5}}, "requires a currency"),
        ({"limits": {"max_ammount": 5}}, "unknown key.*max_ammount"),
        ({"resource": "internal"}, "'resource' must be a mapping"),
        ({"purpose": 7}, "'purpose' must be a string"),
        ({"expires": "someday"}, "cannot parse expiry"),
        ({"approver_role": 3}, "'approver_role' must be a string"),
        ({"principal": ""}, "must not be empty"),
    ],
)
def test_malformed_grants_are_rejected_with_the_offending_value(
    override: dict[str, Any], message: str
) -> None:
    with pytest.raises(GrantLoadError, match=message):
        Grant.from_dict(raw(**override))


def test_granted_by_is_split_into_policy_and_version_only_when_no_version_is_given() -> None:
    split = Grant.from_dict(raw(granted_by="wealth_platform_policy_v14"))
    assert (split.granted_by, split.policy_version) == ("wealth_platform_policy", "v14")
    explicit = Grant.from_dict(raw(granted_by="wealth_platform_policy_v14", policy_version="v15"))
    assert (explicit.granted_by, explicit.policy_version) == ("wealth_platform_policy_v14", "v15")
    plain = Grant.from_dict(raw(granted_by="policy"))
    assert (plain.granted_by, plain.policy_version) == ("policy", "")


def test_a_naive_expiry_is_refused_when_building_a_grant_in_code() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Grant("g", "p", Action.CALL, "c", expires=datetime(2030, 1, 1))


def test_a_grant_needs_an_id_a_principal_and_a_capability() -> None:
    for blank in ("grant_id", "principal", "capability"):
        fields = {"grant_id": "g", "principal": "p", "capability": "c", blank: ""}
        with pytest.raises(GrantLoadError, match=blank):
            Grant(action=Action.CALL, **fields)


def test_a_grant_is_valid_through_its_expiry_instant_and_expired_after_it() -> None:
    expiry = datetime(2030, 1, 1, tzinfo=UTC)
    grant = Grant("g", "p", Action.CALL, "c", expires=expiry)
    assert not grant.is_expired(expiry)
    assert grant.is_expired(expiry + timedelta(microseconds=1))


def test_is_expired_needs_an_aware_now() -> None:
    grant = Grant("g", "p", Action.CALL, "c", expires=datetime(2030, 1, 1, tzinfo=UTC))
    assert not grant.is_expired(datetime(2029, 1, 1, tzinfo=UTC))
    assert grant.is_expired(datetime(2031, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="timezone-aware"):
        grant.is_expired(datetime(2029, 1, 1))


def test_a_resource_selector_turns_lists_into_tuples_and_refuses_a_bare_string() -> None:
    assert ResourceSelector(["public", "internal"]).data_classes == ("public", "internal")  # type: ignore[arg-type]
    with pytest.raises(GrantLoadError):
        ResourceSelector("internal")  # type: ignore[arg-type]


# -- Files -----------------------------------------------------------------------------------


@pytest.mark.parametrize("shape", [lambda g: [g], lambda g: {"grants": [g]}], ids=["list", "keyed"])
def test_a_grants_file_is_a_list_or_a_grants_key(tmp_path: Path, shape: Any) -> None:
    path = tmp_path / "grants.yaml"
    path.write_text(json.dumps(shape(raw())))  # JSON is valid YAML
    assert [g.grant_id for g in load_grants_file(path)] == ["g1"]


def test_an_empty_grants_file_is_no_grants(tmp_path: Path) -> None:
    (tmp_path / "grants.yaml").write_text("")
    assert load_grants_file(tmp_path / "grants.yaml") == []


def test_a_bad_grant_error_names_the_file_and_the_position(tmp_path: Path) -> None:
    path = tmp_path / "grants.yaml"
    path.write_text(json.dumps([raw(), raw(grant_id="g2", efect="allow")]))
    with pytest.raises(GrantLoadError) as exc_info:
        load_grants_file(path)
    assert str(path) in str(exc_info.value)
    assert "grant[1]" in str(exc_info.value)


def test_grants_file_errors(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_grants_file(tmp_path / "missing.yaml")
    (tmp_path / "scalar.yaml").write_text("just text")
    with pytest.raises(GrantLoadError, match="expected a list"):
        load_grants_file(tmp_path / "scalar.yaml")
    (tmp_path / "bad.yaml").write_text("a: [unclosed")
    with pytest.raises(GrantLoadError, match="cannot parse"):
        load_grants_file(tmp_path / "bad.yaml")
    (tmp_path / "entry.yaml").write_text("- just a string\n")
    with pytest.raises(GrantLoadError, match=r"grant\[0\].*expected a mapping"):
        load_grants_file(tmp_path / "entry.yaml")


# -- Decision --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcome", "allowed"),
    [
        (Outcome.ALLOW, True),
        (Outcome.ALLOW_WITH_OBLIGATIONS, True),
        (Outcome.REQUIRE_APPROVAL, False),
        (Outcome.DENY, False),
    ],
)
def test_only_allow_outcomes_count_as_allowed(outcome: Outcome, allowed: bool) -> None:
    decision = Decision(outcome, "X", "why", "p", Action.CALL, "c")
    assert decision.allowed is allowed
    assert decision.to_dict()["outcome"] == str(outcome)
