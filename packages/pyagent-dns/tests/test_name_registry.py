"""Tests for NameRegistry: versioning, discovery, revocation, and expiry."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from pyagent_dns.records import RecordKind, RecordStatus
from pyagent_dns.registry import NameRegistry
from pyagent_dns.signing import VerificationStatus

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pyagent_dns.records import NameRecord
    from pyagent_dns.signing import TrustedKeys

    from .conftest import ControllableClock


# -- Versions --------------------------------------------------------------------------------


def test_get_returns_the_highest_version_by_semver_not_by_string(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register_many(make_record("t", version=v) for v in ("1.9.0", "1.10.0", "1.2.0"))
    record = reg.get("t")
    assert record is not None
    assert record.version == "1.10.0"


def test_a_release_candidate_is_not_preferred_over_its_release(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register_many([make_record("t", version="1.0.0"), make_record("t", version="1.0.0-rc1")])
    record = reg.get("t")
    assert record is not None
    assert record.version == "1.0.0"


def test_two_versions_coexist_and_an_explicit_version_returns_exactly_that_one(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register_many([make_record("t", version="1.0.0"), make_record("t", version="2.0.0")])
    assert len(reg) == reg.count == 2
    old = reg.get("t", "1.0.0")
    assert old is not None
    assert old.version == "1.0.0"
    assert reg.get("t", "1.5.0") is None
    assert reg.get("nope") is None


def test_the_newest_version_that_is_usable_wins_over_a_newer_revoked_one(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register_many([make_record("t", version="1.0.0"), make_record("t", version="2.0.0")])
    reg.revoke("t", "2.0.0")
    record = reg.get("t")
    assert record is not None
    assert record.version == "1.0.0"


def test_a_name_whose_every_version_is_revoked_still_resolves_so_it_can_be_explained(
    make_record: Callable[..., NameRecord],
) -> None:
    """'This name was revoked' and 'this name never existed' are different audit facts."""
    reg = NameRegistry()
    reg.register(make_record("t", version="1.0.0"))
    reg.revoke("t")
    record = reg.get("t")
    assert record is not None
    assert reg.status_of("t", "1.0.0") == RecordStatus.REVOKED


# -- Discovery -------------------------------------------------------------------------------


def test_discover_matches_records_whose_capabilities_include_every_required_one(
    registry: NameRegistry,
) -> None:
    assert [r.name for r in registry.discover({"read_positions"})] == ["portfolio-data.reader"]
    assert [r.name for r in registry.discover({"read_positions", "read_holdings"})] == [
        "portfolio-data.reader"
    ]
    assert registry.discover({"read_positions", "read_vault"}) == []
    assert {r.name for r in registry.discover()} == {
        "portfolio-data.reader",
        "client-vault-reader",
        "public-docs.reader",
    }


def test_discover_filters_by_kind(
    registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    registry.register(make_record("lead", kind=RecordKind.AGENT, capabilities=("plan",)))
    assert [r.name for r in registry.discover(kind=RecordKind.AGENT)] == ["lead"]
    assert "lead" not in {r.name for r in registry.discover(kind=RecordKind.TOOL)}


def test_discover_leaves_out_unverified_and_tampered_records_by_default(
    registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    registry.register_many(
        [
            make_record("unsigned", capabilities=("x",), sign=False),
            make_record("forged", capabilities=("x",), tamper=True),
        ]
    )
    assert registry.discover({"x"}) == []
    assert {r.name for r in registry.discover({"x"}, verified_only=False)} == {"unsigned", "forged"}


def test_discover_returns_the_newest_verified_version_when_a_newer_one_is_unverified(
    registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    """A planted unsigned 9.9.9 must not hide the legitimately signed 3.2.1 from discovery."""
    registry.register(make_record("portfolio-data.reader", version="9.9.9", sign=False))
    (found,) = registry.discover({"read_positions"})
    assert found.version == "3.2.1"


def test_discover_uses_the_newest_version_that_actually_has_the_capability(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys
) -> None:
    reg = NameRegistry(trusted_keys)
    reg.register_many(
        [
            make_record("t", version="1.0.0", capabilities=("read", "write")),
            make_record("t", version="2.0.0", capabilities=("read",)),
        ]
    )
    assert [r.version for r in reg.discover({"read"})] == ["2.0.0"]
    assert [r.version for r in reg.discover({"write"})] == ["1.0.0"]


def test_discover_skips_revoked_and_expired_records(
    registry: NameRegistry, frozen_clock: ControllableClock, make_record: Callable[..., NameRecord]
) -> None:
    registry.register(
        make_record(
            "short-lived",
            capabilities=("tmp",),
            expires=frozen_clock.now_utc() + timedelta(hours=1),
        )
    )
    assert [r.name for r in registry.discover({"tmp"})] == ["short-lived"]
    frozen_clock.advance(2 * 3600)
    assert registry.discover({"tmp"}) == []
    registry.revoke("public-docs.reader")
    assert "public-docs.reader" not in {r.name for r in registry.discover()}


# -- Revocation ------------------------------------------------------------------------------


def test_revoke_reports_a_change_once_and_bumps_the_generation(registry: NameRegistry) -> None:
    before = registry.generation
    assert registry.revoke("portfolio-data.reader") is True
    assert registry.generation > before
    after = registry.generation
    assert registry.revoke("portfolio-data.reader") is False
    assert registry.generation == after
    assert registry.revoke("nope") is False
    assert registry.status_of("portfolio-data.reader", "3.2.1") == RecordStatus.REVOKED


def test_revoking_a_record_leaves_its_signature_and_fingerprint_intact(
    registry: NameRegistry,
) -> None:
    """The owner's signed bytes are evidence. A revoked record must read 'verified, revoked', never 'failed'."""
    before = registry.get("portfolio-data.reader")
    assert before is not None
    registry.revoke("portfolio-data.reader")
    after = registry.get("portfolio-data.reader")
    assert after is not None
    assert after.fingerprint == before.fingerprint
    assert (
        after.status == RecordStatus.ACTIVE
    )  # as published; status_of reports the effective status
    assert registry.verify("portfolio-data.reader") == VerificationStatus.VERIFIED


def test_revoking_a_name_without_a_version_revokes_every_version(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register_many([make_record("t", version="1.0.0"), make_record("t", version="2.0.0")])
    assert reg.revoke("t")
    assert {reg.status_of("t", v) for v in ("1.0.0", "2.0.0")} == {RecordStatus.REVOKED}


def test_a_record_the_owner_declared_revoked_cannot_be_revoked_again(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register(make_record("t", status=RecordStatus.REVOKED))
    assert reg.status_of("t", "3.2.1") == RecordStatus.REVOKED
    assert reg.revoke("t") is False


def test_registering_a_revoked_name_and_version_again_does_not_bring_it_back(
    registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    registry.revoke("portfolio-data.reader")
    registry.register(make_record("portfolio-data.reader"))
    assert registry.status_of("portfolio-data.reader", "3.2.1") == RecordStatus.REVOKED


def test_remove_deletes_one_version_or_all_and_clears_their_revocation(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register_many([make_record("t", version="1.0.0"), make_record("t", version="2.0.0")])
    reg.revoke("t", "1.0.0")
    reg.remove("t", "1.0.0")
    assert reg.get("t", "1.0.0") is None
    assert len(reg) == 1
    reg.register(make_record("t", version="1.0.0"))
    assert reg.status_of("t", "1.0.0") == RecordStatus.ACTIVE
    reg.remove("t")
    assert "t" not in reg
    assert reg.count == 0


# -- Expiry ----------------------------------------------------------------------------------


def test_expire_reports_each_version_once_and_deletes_nothing(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register_many(
        [
            make_record("old", expires=datetime(2025, 1, 1, tzinfo=UTC)),
            make_record("new", expires=datetime(2099, 1, 1, tzinfo=UTC)),
        ]
    )
    now = datetime(2026, 6, 1, tzinfo=UTC)
    assert reg.expire(now) == ["old"]
    assert reg.expire(now) == []
    assert "old" in reg


def test_a_second_version_of_a_name_is_reported_when_it_expires_later(
    make_record: Callable[..., NameRecord],
) -> None:
    """Tracking by name alone would swallow the second version's expiry."""
    reg = NameRegistry()
    reg.register_many(
        [
            make_record("t", version="1.0.0", expires=datetime(2026, 1, 1, tzinfo=UTC)),
            make_record("t", version="2.0.0", expires=datetime(2027, 1, 1, tzinfo=UTC)),
        ]
    )
    assert reg.expire(datetime(2026, 6, 1, tzinfo=UTC)) == ["t"]
    assert reg.expire(datetime(2027, 6, 1, tzinfo=UTC)) == ["t"]


def test_re_registering_an_expired_record_re_arms_its_expiry_report(
    make_record: Callable[..., NameRecord],
) -> None:
    reg = NameRegistry()
    reg.register(make_record("t", expires=datetime(2026, 1, 1, tzinfo=UTC)))
    assert reg.expire(datetime(2026, 6, 1, tzinfo=UTC)) == ["t"]
    reg.register(make_record("t", expires=datetime(2026, 9, 1, tzinfo=UTC)))
    assert reg.expire(datetime(2026, 7, 1, tzinfo=UTC)) == []
    assert reg.expire(datetime(2026, 10, 1, tzinfo=UTC)) == ["t"]


def test_expire_defaults_to_the_injected_clock_and_rejects_a_naive_time(
    make_record: Callable[..., NameRecord], frozen_clock: ControllableClock
) -> None:
    reg = NameRegistry(clock=frozen_clock)
    reg.register(make_record("t", expires=frozen_clock.now_utc() + timedelta(minutes=5)))
    assert reg.expire() == []
    frozen_clock.advance(600)
    assert reg.expire() == ["t"]
    with pytest.raises(ValueError, match="timezone-aware"):
        reg.expire(datetime(2026, 1, 1))


# -- Verification and listing ----------------------------------------------------------------


def test_with_no_trusted_keys_nothing_is_verified(make_record: Callable[..., NameRecord]) -> None:
    reg = NameRegistry()
    reg.register(make_record("t"))
    assert reg.verify("t") == VerificationStatus.UNVERIFIED
    assert reg.verify("never-registered") == VerificationStatus.UNVERIFIED


def test_changing_the_trusted_keys_changes_verification_and_the_generation(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys
) -> None:
    reg = NameRegistry()
    reg.register(make_record("t"))
    before = reg.generation
    reg.trusted_keys = trusted_keys
    assert reg.generation > before
    assert reg.verify("t") == VerificationStatus.VERIFIED


def test_list_records_reports_effective_status_and_computed_verification(
    registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    registry.register(make_record("zz-unsigned", sign=False))
    registry.revoke("client-vault-reader")
    info = {i.name: i for i in registry.list_records()}
    assert info["portfolio-data.reader"].verification == VerificationStatus.VERIFIED
    assert info["zz-unsigned"].verification == VerificationStatus.UNVERIFIED
    assert info["client-vault-reader"].status == RecordStatus.REVOKED
    assert info["client-vault-reader"].verification == VerificationStatus.VERIFIED
    assert [i.name for i in registry.list_records()] == sorted(info)


def test_a_registry_loads_from_a_directory(
    tmp_path: Path, make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys
) -> None:
    (tmp_path / "signed.json").write_text(json.dumps(make_record("on.disk").to_dict()))
    reg = NameRegistry.from_directory(tmp_path, trusted_keys=trusted_keys)
    assert "on.disk" in reg
    assert reg.verify("on.disk") == VerificationStatus.VERIFIED


def test_the_registry_reads_time_from_its_injected_clock(frozen_clock: ControllableClock) -> None:
    reg = NameRegistry(clock=frozen_clock)
    assert reg.now() == frozen_clock.now_utc()
    frozen_clock.advance(60)
    assert reg.now() == frozen_clock.now_utc()
    assert reg.clock is frozen_clock
