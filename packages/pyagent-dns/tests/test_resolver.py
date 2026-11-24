"""Tests for Resolver: what a resolution carries, and when the cache may and may not be used."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from pyagent_dns.records import RecordStatus
from pyagent_dns.registry import NameRegistry
from pyagent_dns.resolver import Resolver
from pyagent_dns.signing import VerificationStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest
    from pyagent_dns.records import NameRecord

    from .conftest import ControllableClock


def test_a_resolution_carries_the_exact_version_fingerprint_status_and_verification(
    resolver: Resolver, registry: NameRegistry
) -> None:
    resolution = resolver.resolve("portfolio-data.reader")
    assert resolution is not None
    record = registry.get("portfolio-data.reader")
    assert record is not None
    assert resolution.record == record
    assert resolution.version == "3.2.1"
    assert resolution.fingerprint == record.fingerprint
    assert resolution.verified is True
    assert resolution.verification == VerificationStatus.VERIFIED
    assert resolution.status == RecordStatus.ACTIVE
    assert resolution.from_cache is False


def test_an_unknown_name_resolves_to_none_rather_than_raising(resolver: Resolver) -> None:
    assert resolver.resolve("nope") is None
    assert resolver.resolve_fresh("nope") is None


def test_a_second_resolve_within_the_ttl_is_served_from_the_cache(
    resolver: Resolver, frozen_clock: ControllableClock
) -> None:
    first = resolver.resolve("portfolio-data.reader")
    frozen_clock.advance(299)
    again = resolver.resolve("portfolio-data.reader")
    assert first is not None
    assert again is not None
    assert again.from_cache is True
    assert again.resolved_at == first.resolved_at
    assert again.record == first.record


def test_advancing_past_the_ttl_forces_a_fresh_resolution(
    resolver: Resolver, frozen_clock: ControllableClock
) -> None:
    first = resolver.resolve("portfolio-data.reader")
    frozen_clock.advance(301)
    again = resolver.resolve("portfolio-data.reader")
    assert first is not None
    assert again is not None
    assert again.from_cache is False
    assert again.resolved_at > first.resolved_at


def test_a_zero_ttl_is_never_served_from_the_cache(
    make_record: Callable[..., NameRecord], trusted_keys: object, frozen_clock: ControllableClock
) -> None:
    reg = NameRegistry(trusted_keys, clock=frozen_clock)  # type: ignore[arg-type]
    reg.register(make_record("t", ttl_seconds=0))
    res = Resolver(reg)
    res.resolve("t")
    again = res.resolve("t")
    assert again is not None
    assert again.from_cache is False


def test_resolve_fresh_ignores_a_live_cache_entry(resolver: Resolver) -> None:
    resolver.resolve("portfolio-data.reader")
    fresh = resolver.resolve_fresh("portfolio-data.reader")
    assert fresh is not None
    assert fresh.from_cache is False


def test_any_registry_change_drops_the_cache(
    resolver: Resolver, registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    resolver.resolve("portfolio-data.reader")
    assert resolver.cache_size == 1
    registry.register(make_record("portfolio-data.reader", version="4.0.0"))
    assert resolver.cache_size == 0
    newest = resolver.resolve("portfolio-data.reader")
    assert newest is not None
    assert newest.version == "4.0.0"


def test_a_revoked_record_is_never_served_from_the_cache_and_says_why(
    resolver: Resolver, registry: NameRegistry
) -> None:
    before = resolver.resolve("portfolio-data.reader")
    assert before is not None
    registry.revoke("portfolio-data.reader")
    after = resolver.resolve("portfolio-data.reader")
    assert after is not None
    assert after.from_cache is False
    assert after.status == RecordStatus.REVOKED
    assert after.verification == VerificationStatus.VERIFIED  # the signature is still the owner's
    assert after.fingerprint == before.fingerprint  # a log naming it still names the same bytes
    assert resolver.cache_size == 0


def test_an_expired_record_is_not_served_from_the_cache(
    make_record: Callable[..., NameRecord], trusted_keys: object, frozen_clock: ControllableClock
) -> None:
    reg = NameRegistry(trusted_keys, clock=frozen_clock)  # type: ignore[arg-type]
    reg.register(
        make_record("t", expires=frozen_clock.now_utc() + timedelta(seconds=100), ttl_seconds=1000)
    )
    res = Resolver(reg)
    assert res.resolve("t") is not None
    assert res.resolve("t").from_cache is True  # type: ignore[union-attr]
    frozen_clock.advance(101)  # still inside the 1000s ttl, but the record has expired
    after = res.resolve("t")
    assert after is not None
    assert after.from_cache is False
    assert res.cache_size == 0


def test_a_forged_record_is_cached_only_for_its_ttl_so_a_flood_does_not_re_verify(
    registry: NameRegistry,
    resolver: Resolver,
    frozen_clock: ControllableClock,
    make_record: Callable[..., NameRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry.register(make_record("portfolio-data.reader", tamper=True))
    calls = 0
    real_verify = registry.verify

    def counting_verify(name: str, version: str | None = None) -> VerificationStatus:
        nonlocal calls
        calls += 1
        return real_verify(name, version)

    monkeypatch.setattr(registry, "verify", counting_verify)
    for _ in range(50):
        resolution = resolver.resolve("portfolio-data.reader")
        assert resolution is not None
        assert resolution.verification == VerificationStatus.FAILED
    assert calls == 1
    frozen_clock.advance(301)
    resolver.resolve("portfolio-data.reader")
    assert calls == 2


def test_changing_the_trusted_keys_invalidates_cached_verification(
    resolver: Resolver, registry: NameRegistry
) -> None:
    first = resolver.resolve("portfolio-data.reader")
    assert first is not None
    assert first.verified
    registry.trusted_keys = None
    second = resolver.resolve("portfolio-data.reader")
    assert second is not None
    assert second.verification == VerificationStatus.UNVERIFIED


def test_invalidate_drops_one_name_or_everything(resolver: Resolver) -> None:
    for name in ("portfolio-data.reader", "client-vault-reader"):
        resolver.resolve(name)
    resolver.invalidate("portfolio-data.reader")
    assert resolver.cache_size == 1
    resolver.invalidate()
    assert resolver.cache_size == 0


def test_resolve_capability_resolves_every_usable_record_declaring_it(
    resolver: Resolver, registry: NameRegistry, make_record: Callable[..., NameRecord]
) -> None:
    registry.register(make_record("second.reader", capabilities=("read_positions",), sign=False))
    found = {r.record.name: r for r in resolver.resolve_capability("read_positions")}
    assert set(found) == {"portfolio-data.reader", "second.reader"}
    assert found["second.reader"].verification == VerificationStatus.UNVERIFIED
    assert resolver.resolve_capability("nothing_declares_this") == []


def test_the_resolver_shares_the_registry_clock_unless_given_its_own(
    registry: NameRegistry, frozen_clock: ControllableClock
) -> None:
    shared = Resolver(registry).resolve("portfolio-data.reader")
    own = Resolver(registry, clock=lambda: 42.0).resolve("portfolio-data.reader")
    assert shared is not None
    assert own is not None
    assert shared.resolved_at == frozen_clock()
    assert own.resolved_at == 42.0
