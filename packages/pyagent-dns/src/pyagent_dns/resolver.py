"""Name and capability resolution with TTL caching."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyagent_dns.records import NameRecord, RecordStatus
from pyagent_dns.signing import VerificationStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyagent_dns.registry import NameRegistry


@dataclass(frozen=True)
class Resolution:
    """The result of resolving a name: a record, and what is known about it right now.

    Lifecycle and verification are separate facts. ``status`` is the effective lifecycle
    status, including operator revocation. ``verification`` is computed by the verifier, and
    a record cannot declare its own verification outcome.

    Args:
        record: The record as published and signed.
        version: Exact version resolved.
        fingerprint: Digest of the signed bytes. Stable across revocation, so a decision
            log can name exactly what was resolved.
        resolved_at: Epoch seconds, from the resolver's clock.
        verified: Whether ``verification`` is ``VERIFIED``.
        verification: Signature verification outcome.
        status: Effective lifecycle status.
        from_cache: Whether this was served from the TTL cache.
    """

    record: NameRecord
    version: str
    fingerprint: str
    resolved_at: float
    verified: bool
    verification: VerificationStatus
    status: RecordStatus = RecordStatus.ACTIVE
    from_cache: bool = False


class Resolver:
    """Resolve names to verified records, caching each result for the record's TTL.

    The cache is dropped whenever the registry changes, and a revoked or expired record is
    never served from it. Resolution is a local lookup plus a signature check. It never
    connects to the record's endpoint.

    Args:
        registry: The registry to resolve against.
        clock: Epoch-seconds time source. Defaults to the registry's, so TTLs and record
            expiry always agree.
    """

    def __init__(self, registry: NameRegistry, *, clock: Callable[[], float] | None = None) -> None:
        self._registry = registry
        self._clock = clock or registry.clock
        self._cache: dict[tuple[str, str], Resolution] = {}
        self._seen_generation = registry.generation

    @property
    def cache_size(self) -> int:
        """Number of cached resolutions."""
        self._drop_stale_cache()
        return len(self._cache)

    def _drop_stale_cache(self) -> None:
        if self._registry.generation != self._seen_generation:
            self._cache.clear()
            self._seen_generation = self._registry.generation

    def invalidate(self, name: str | None = None) -> None:
        """Drop the whole cache, or only the entries for ``name``."""
        if name is None:
            self._cache.clear()
        else:
            for key in [k for k in self._cache if k[0] == name]:
                del self._cache[key]

    def _status(self, record: NameRecord) -> RecordStatus:
        return self._registry.status_of(record.name, record.version) or record.status

    def _is_live(self, record: NameRecord) -> bool:
        return self._status(record) != RecordStatus.REVOKED and not record.is_expired(
            self._registry.now()
        )

    def _build(self, record: NameRecord) -> Resolution:
        verification = self._registry.verify(record.name, record.version)
        resolution = Resolution(
            record=record,
            version=record.version,
            fingerprint=record.fingerprint,
            resolved_at=self._clock(),
            verified=verification == VerificationStatus.VERIFIED,
            verification=verification,
            status=self._status(record),
        )
        key = (record.name, record.version)
        if self._is_live(record):
            self._cache[key] = resolution
        else:
            self._cache.pop(key, None)
        return resolution

    def resolve(self, name: str, version: str | None = None) -> Resolution | None:
        """Resolve ``name``, using the cache while the entry is within the record's TTL.

        Returns ``None`` only if the name was never registered. A revoked or expired record
        still resolves, with that fact in ``status``, because "revoked" and "never existed"
        are different audit facts.
        """
        self._drop_stale_cache()
        record = self._registry.get(name, version)
        if record is None:
            return None
        cached = self._cache.get((record.name, record.version))
        if (
            cached is not None
            and self._is_live(record)
            and self._clock() - cached.resolved_at < record.ttl_seconds
        ):
            return dataclasses.replace(cached, from_cache=True)
        return self._build(record)

    def resolve_fresh(self, name: str, version: str | None = None) -> Resolution | None:
        """Resolve and verify without consulting the cache. Used for high-risk actions."""
        self._drop_stale_cache()
        record = self._registry.get(name, version)
        return None if record is None else self._build(record)

    def resolve_capability(self, capability: str) -> list[Resolution]:
        """Resolve every usable record that declares ``capability``, verified or not."""
        found = self._registry.discover({capability}, verified_only=False)
        return [r for record in found if (r := self.resolve(record.name, record.version))]
