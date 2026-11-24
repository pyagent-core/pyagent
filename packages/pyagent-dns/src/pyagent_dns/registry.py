"""In-memory, file-backed registry of NameRecords."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pyagent_dns.records import (
    NameRecord,
    RecordInfo,
    RecordKind,
    RecordStatus,
    ensure_aware,
    load_records_directory,
    version_key,
)
from pyagent_dns.signing import VerificationStatus, verify_record

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from pyagent_dns.signing import TrustedKeys

_Key = tuple[str, str]


class NameRegistry:
    """Versioned store of signed records, with capability discovery and revocation.

    Records are keyed by ``(name, version)`` so several versions of one name can coexist.
    ``revoke`` records the revocation in the registry and leaves the stored record exactly
    as the owner signed it. Rewriting the record's ``status`` would break its signature and
    change its fingerprint, and an audit log would then report a legitimately revoked record
    as ``failed``. Use :meth:`status_of` for the effective lifecycle status.

    Revocation lasts for the registry's lifetime: re-registering a revoked ``(name,
    version)`` does not restore it. Reload from files to clear it.

    Not thread-safe. Like ``ProviderRegistry``, it assumes single-process, event-loop use;
    serialize access yourself if you mutate it from several threads.

    Args:
        trusted_keys: Keys records are verified against. With none, every record is
            ``UNVERIFIED``.
        clock: Returns the current time in epoch seconds. Inject one in tests instead of
            sleeping.
    """

    def __init__(
        self,
        trusted_keys: TrustedKeys | None = None,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._trusted_keys = trusted_keys
        self._clock = clock
        self._records: dict[_Key, NameRecord] = {}
        self._revoked: set[_Key] = set()
        self._reported_expired: set[_Key] = set()
        self._generation = 0

    @property
    def trusted_keys(self) -> TrustedKeys | None:
        """The keys records are verified against."""
        return self._trusted_keys

    @trusted_keys.setter
    def trusted_keys(self, value: TrustedKeys | None) -> None:
        self._trusted_keys = value
        self._generation += 1

    @property
    def clock(self) -> Callable[[], float]:
        """The time source, in epoch seconds."""
        return self._clock

    @property
    def generation(self) -> int:
        """Counter that increases on every change that could alter a resolution."""
        return self._generation

    @property
    def count(self) -> int:
        """Number of stored records, counting each version."""
        return len(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def __contains__(self, name: str) -> bool:
        return any(record_name == name for record_name, _ in self._records)

    def now(self) -> datetime:
        """The current time as an aware UTC datetime, from the injected clock."""
        return datetime.fromtimestamp(self._clock(), UTC)

    def register(self, record: NameRecord) -> None:
        """Store a record, replacing any record with the same name and version.

        Unsigned and unverifiable records are accepted, because a registry may hold them for
        review. Verification is reported, and enforced at authorization time.
        """
        self.register_many([record])

    def register_many(self, records: Iterable[NameRecord]) -> None:
        """Store several records as one change."""
        changed = False
        for record in records:
            key = (record.name, record.version)
            self._records[key] = record
            self._reported_expired.discard(key)
            changed = True
        if changed:
            self._generation += 1

    @classmethod
    def from_directory(
        cls, path: str | Path, *, trusted_keys: TrustedKeys | None = None
    ) -> NameRegistry:
        """Build a registry from every record file under a directory."""
        registry = cls(trusted_keys=trusted_keys)
        registry.register_many(load_records_directory(path))
        return registry

    def status_of(self, name: str, version: str) -> RecordStatus | None:
        """Effective lifecycle status of one version, or ``None`` if it is not stored.

        ``REVOKED`` if the owner declared it or an operator revoked it here.
        """
        record = self._records.get((name, version))
        if record is None:
            return None
        if (name, version) in self._revoked:
            return RecordStatus.REVOKED
        return record.status

    def _usable(self, record: NameRecord, now: datetime) -> bool:
        status = self.status_of(record.name, record.version)
        return status != RecordStatus.REVOKED and not record.is_expired(now)

    def _versions(self, name: str) -> list[NameRecord]:
        """Stored versions of ``name``, newest first."""
        matching = [record for (n, _), record in self._records.items() if n == name]
        return sorted(matching, key=lambda r: (version_key(r.version), r.version), reverse=True)

    def get(self, name: str, version: str | None = None) -> NameRecord | None:
        """Return a record as published.

        With ``version``, returns exactly that version or ``None``. Without it, returns the
        newest version that is neither revoked nor expired. If every version is revoked or
        expired it returns the newest anyway, so a caller can tell "this name was revoked"
        from "this name never existed". Check :meth:`status_of` before relying on the result.
        """
        if version is not None:
            return self._records.get((name, version))
        versions = self._versions(name)
        if not versions:
            return None
        now = self.now()
        return next((r for r in versions if self._usable(r, now)), versions[0])

    def list_records(self) -> list[RecordInfo]:
        """Summarize every stored record, including its computed verification status."""
        return [
            RecordInfo(
                name=record.name,
                kind=record.kind,
                version=record.version,
                status=self.status_of(record.name, record.version) or record.status,
                owner=record.owner,
                fingerprint=record.fingerprint,
                verification=self.verify(record.name, record.version),
            )
            for _, record in sorted(self._records.items())
        ]

    def discover(
        self,
        required_capabilities: set[str] | None = None,
        *,
        kind: RecordKind | None = None,
        verified_only: bool = True,
    ) -> list[NameRecord]:
        """Find records whose capabilities include every required capability.

        Matching is exact set inclusion, the same semantics as ``ProviderRegistry.discover``.
        Each name contributes at most its newest version that is usable (not revoked or
        expired) and passes the filters. Unverified records are excluded unless
        ``verified_only`` is False; discovery never implies permission to call.
        """
        required = required_capabilities or set()
        now = self.now()
        found: list[NameRecord] = []
        for name in sorted({n for n, _ in self._records}):
            for record in self._versions(name):
                if not self._usable(record, now):
                    continue
                if kind is not None and record.kind != kind:
                    continue
                if not required <= set(record.capabilities):
                    continue
                if (
                    verified_only
                    and self.verify(record.name, record.version) != VerificationStatus.VERIFIED
                ):
                    continue
                found.append(record)
                break
        return found

    def verify(self, name: str, version: str | None = None) -> VerificationStatus:
        """Verify a stored record's signature. ``UNVERIFIED`` if absent or no keys are set."""
        record = self.get(name, version)
        if record is None or self._trusted_keys is None:
            return VerificationStatus.UNVERIFIED
        return verify_record(record, self._trusted_keys)

    def expire(self, now: datetime | None = None) -> list[str]:
        """Report names whose versions have newly crossed their expiry. Nothing is deleted.

        An expired record stays stored so a decision log that names its fingerprint can
        still be explained. Each ``(name, version)`` is reported once.
        """
        current = self.now() if now is None else ensure_aware(now, "now")
        newly = [
            key
            for key, record in self._records.items()
            if key not in self._reported_expired and record.is_expired(current)
        ]
        if newly:
            self._reported_expired.update(newly)
            self._generation += 1
        return sorted({name for name, _ in newly})

    def revoke(self, name: str, version: str | None = None) -> bool:
        """Revoke one version, or every version of ``name``. Returns whether anything changed."""
        keys = [k for k in self._records if k[0] == name and (version is None or k[1] == version)]
        newly = [k for k in keys if self.status_of(*k) != RecordStatus.REVOKED]
        if newly:
            self._revoked.update(newly)
            self._generation += 1
        return bool(newly)

    def remove(self, name: str, version: str | None = None) -> None:
        """Delete one version, or every version of ``name``, including its revocation."""
        keys = [k for k in self._records if k[0] == name and (version is None or k[1] == version)]
        for key in keys:
            del self._records[key]
            self._revoked.discard(key)
            self._reported_expired.discard(key)
        if keys:
            self._generation += 1
