"""Data model and loaders for signed NameRecord objects in the naming plane."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from pyagent_dns.signing import VerificationStatus

# The closed vocabulary for data classes, ordered least to most sensitive. It matches
# SENSITIVITY_ORDER in pyagent-context by value, not by import, so this package does
# not depend on pyagent-context.
SENSITIVITY_ORDER: dict[str, int] = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
VALID_DATA_CLASSES: frozenset[str] = frozenset(SENSITIVITY_ORDER)

_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class RecordLoadError(ValueError):
    """Raised when a record is malformed, whether loaded from a file or built in code."""


def version_key(version: str) -> tuple[Any, ...]:
    """Return a sort key implementing semver 2.0 precedence for ``version``.

    A pre-release sorts below its release (``1.0.0-rc1 < 1.0.0``). Build metadata is
    ignored, as the semver specification requires.

    Raises:
        RecordLoadError: If ``version`` is not a semantic version.
    """
    match = _SEMVER.match(version)
    if match is None:
        raise RecordLoadError(f"Invalid version '{version}': expected semver such as '1.4.2'")
    major, minor, patch, prerelease = match.groups()
    if prerelease is None:
        return (int(major), int(minor), int(patch), 1, ())
    identifiers = tuple(
        (0, int(p), "") if p.isdigit() else (1, 0, p) for p in prerelease.split(".")
    )
    return (int(major), int(minor), int(patch), 0, identifiers)


def ensure_aware(value: datetime, what: str) -> datetime:
    """Return ``value`` unchanged if timezone-aware, else raise ``ValueError``.

    A naive datetime is ambiguous: ``astimezone`` would read it in the host's timezone,
    so the same record would produce different canonical bytes on different machines.
    """
    if value.tzinfo is None:
        raise ValueError(f"{what} must be timezone-aware, got naive datetime {value.isoformat()}")
    return value


def parse_expiry(value: Any, *, where: str, error: type[ValueError]) -> datetime | None:
    """Normalize a YAML/JSON expiry value to an aware UTC datetime, or ``None``.

    Accepts a ``datetime`` (naive values are read as UTC), a ``date``, or an ISO 8601 string.
    A bare date means the end of that day (23:59:59 UTC), so ``2026-12-31`` stays valid
    through December 31st.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=UTC)).astimezone(UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, 23, 59, 59, tzinfo=UTC)
    if isinstance(value, str):
        text = value.strip()
        try:
            # Try a date first: datetime.fromisoformat also accepts "2026-12-31", as midnight,
            # which would make a quoted date expire a day earlier than the same unquoted date.
            return parse_expiry(date.fromisoformat(text), where=where, error=error)
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise error(f"{where}: cannot parse expiry '{value}'") from None
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)
    raise error(f"{where}: unsupported expiry type {type(value).__name__}")


def check_keys(
    data: Mapping[str, Any],
    *,
    required: Iterable[str],
    optional: Iterable[str],
    where: str,
    error: type[ValueError],
) -> None:
    """Reject missing required keys and any unknown key.

    A misspelled key must never fall back to a permissive default. ``efect:
    require_approval`` would otherwise load as an ordinary allow.
    """
    required_keys, optional_keys = set(required), set(optional)
    missing = sorted(required_keys - data.keys())
    if missing:
        raise error(f"{where}: missing required key(s): {', '.join(missing)}")
    unknown = sorted(set(data) - required_keys - optional_keys)
    if unknown:
        allowed = ", ".join(sorted(required_keys | optional_keys))
        raise error(f"{where}: unknown key(s): {', '.join(unknown)} (allowed: {allowed})")


def _string_list(value: Any, *, key: str, where: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise RecordLoadError(f"{where}: '{key}' must be a list of strings, got {value!r}")
    if not all(isinstance(item, str) for item in value):
        raise RecordLoadError(f"{where}: '{key}' must contain only strings, got {list(value)!r}")
    return tuple(value)


class RecordKind(StrEnum):
    """The kind of entity named by a NameRecord."""

    AGENT = "agent"
    TOOL = "tool"
    PROVIDER = "provider"
    DATA = "data"
    APPROVER = "approver"


class RecordStatus(StrEnum):
    """Lifecycle status the record's owner declared inside the signed payload."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


@dataclass(frozen=True)
class Identity:
    """Identity claims and key reference carried by a record.

    Args:
        public_key_fingerprint: ``sha256:`` followed by the hex digest of the signing key.
        public_key: Optional signing key, base64 raw Ed25519 or PEM. Informational only:
            verification never trusts a key supplied by the record itself.
        workload_id: Optional workload identifier, for example a SPIFFE ID.
        signed_by: Name of the signer, a key into the trusted keys file.
    """

    public_key_fingerprint: str
    public_key: str | None = None
    workload_id: str | None = None
    signed_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the identity as a plain dictionary."""
        return {
            "public_key_fingerprint": self.public_key_fingerprint,
            "public_key": self.public_key,
            "workload_id": self.workload_id,
            "signed_by": self.signed_by,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, where: str = "identity") -> Identity:
        """Build an Identity from a mapping, rejecting unknown or missing keys."""
        check_keys(
            data,
            required=["public_key_fingerprint"],
            optional=["public_key", "workload_id", "signed_by"],
            where=where,
            error=RecordLoadError,
        )
        for key in ("public_key_fingerprint", "public_key", "workload_id", "signed_by"):
            value = data.get(key)
            if value is not None and not isinstance(value, str):
                raise RecordLoadError(f"{where}: '{key}' must be a string, got {value!r}")
        return cls(
            public_key_fingerprint=data["public_key_fingerprint"],
            public_key=data.get("public_key"),
            workload_id=data.get("workload_id"),
            signed_by=data.get("signed_by") or "",
        )


@dataclass(frozen=True)
class NameRecord:
    """A versioned record naming an agent, tool, provider, data source, or approver.

    The record is the *naming plane*: it says what something is and who vouches for it.
    It grants nothing. Permissions live in :class:`pyagent_dns.authority.Grant`.

    ``capabilities`` and ``data_classes`` are tuples so that a signed record cannot be
    altered through a shared list. Lists passed to the constructor are converted.

    Args:
        name: Unique identifier, for example ``portfolio-data.reader``.
        kind: Entity type.
        version: Semantic version string.
        endpoint: Invocation URI or reference. Resolution never connects to it.
        identity: Signer and key details.
        schema_hash: ``sha256:`` digest of the capability's schema.
        capabilities: Declared capability names, used for discovery.
        data_classes: Sensitivity classes this record touches; a floor that callers
            cannot understate when authorization is evaluated.
        owner: Responsible team.
        status: Lifecycle status declared by the owner.
        expires: Timezone-aware expiry, or ``None`` for no expiry.
        ttl_seconds: How long a resolution may be cached.
        signature: Base64 Ed25519 signature over :meth:`canonical_bytes`.
        signature_algorithm: Signature algorithm; only ``ed25519`` is supported.
    """

    name: str
    kind: RecordKind
    version: str
    endpoint: str
    identity: Identity
    schema_hash: str
    capabilities: tuple[str, ...]
    data_classes: tuple[str, ...]
    owner: str
    status: RecordStatus = RecordStatus.ACTIVE
    expires: datetime | None = None
    ttl_seconds: int = 300
    signature: str | None = None
    signature_algorithm: str = "ed25519"

    def __post_init__(self) -> None:
        if not self.name:
            raise RecordLoadError("record name must not be empty")
        version_key(self.version)
        for field_name in ("capabilities", "data_classes"):
            value = getattr(self, field_name)
            if isinstance(value, str) or not all(isinstance(item, str) for item in value):
                raise RecordLoadError(
                    f"record '{self.name}': {field_name} must be a sequence of strings, got {value!r}"
                )
            object.__setattr__(self, field_name, tuple(value))
        for data_class in self.data_classes:
            if data_class not in VALID_DATA_CLASSES:
                raise RecordLoadError(
                    f"record '{self.name}': unknown data class '{data_class}'. "
                    f"Expected one of: {sorted(VALID_DATA_CLASSES)}"
                )
        if self.expires is not None:
            ensure_aware(self.expires, f"record '{self.name}' expires")
        if isinstance(self.ttl_seconds, bool) or not isinstance(self.ttl_seconds, int):
            raise RecordLoadError(f"record '{self.name}': ttl_seconds must be an integer")
        if self.ttl_seconds < 0:
            raise RecordLoadError(f"record '{self.name}': ttl_seconds must not be negative")

    def canonical_bytes(self) -> bytes:
        """Return the exact bytes that are signed: sorted-key compact JSON, UTF-8.

        ``signature`` is excluded. The ``_pyagent_dns`` marker is a domain separator, so a
        signature over a record cannot be replayed as a signature in another protocol.
        """
        expires: str | None = None
        if self.expires is not None:
            utc = self.expires.astimezone(UTC)
            expires = utc.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ" if utc.microsecond else "%Y-%m-%dT%H:%M:%SZ"
            )
        payload = {
            "_pyagent_dns": "record/v1",
            "capabilities": list(self.capabilities),
            "data_classes": list(self.data_classes),
            "endpoint": self.endpoint,
            "expires": expires,
            "identity": self.identity.to_dict(),
            "kind": str(self.kind),
            "name": self.name,
            "owner": self.owner,
            "schema_hash": self.schema_hash,
            "signature_algorithm": self.signature_algorithm,
            "status": str(self.status),
            "ttl_seconds": self.ttl_seconds,
            "version": self.version,
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()

    @property
    def fingerprint(self) -> str:
        """``sha256:`` digest of :meth:`canonical_bytes`, the stable name of these exact bytes."""
        return f"sha256:{hashlib.sha256(self.canonical_bytes()).hexdigest()}"

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether the record's expiry has passed at ``now`` (default: current UTC time)."""
        if self.expires is None:
            return False
        current = datetime.now(UTC) if now is None else ensure_aware(now, "now")
        return current > self.expires

    def to_dict(self) -> dict[str, Any]:
        """Return the record as a plain dictionary that :meth:`from_dict` accepts."""
        return {
            "name": self.name,
            "kind": str(self.kind),
            "version": self.version,
            "endpoint": self.endpoint,
            "identity": self.identity.to_dict(),
            "schema_hash": self.schema_hash,
            "capabilities": list(self.capabilities),
            "data_classes": list(self.data_classes),
            "owner": self.owner,
            "status": str(self.status),
            "expires": self.expires.astimezone(UTC).isoformat() if self.expires else None,
            "ttl_seconds": self.ttl_seconds,
            "signature": self.signature,
            "signature_algorithm": self.signature_algorithm,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, where: str = "record") -> NameRecord:
        """Build a record from a mapping.

        Every field without a default in the dataclass is required, and unknown keys are
        rejected, so a typo cannot silently change what is signed or granted.

        Raises:
            RecordLoadError: On a missing, unknown, or malformed field.
        """
        required = ["name", "kind", "version", "endpoint", "identity", "schema_hash"]
        required += ["capabilities", "data_classes", "owner"]
        optional = ["status", "expires", "ttl_seconds", "signature", "signature_algorithm"]
        check_keys(data, required=required, optional=optional, where=where, error=RecordLoadError)
        for key in ("name", "version", "endpoint", "schema_hash", "owner"):
            if not isinstance(data[key], str):
                raise RecordLoadError(f"{where}: '{key}' must be a string, got {data[key]!r}")
        if not isinstance(data["identity"], dict):
            raise RecordLoadError(f"{where}: 'identity' must be a mapping")
        signature = data.get("signature")
        if signature is not None and not isinstance(signature, str):
            raise RecordLoadError(f"{where}: 'signature' must be a string")
        try:
            kind = RecordKind(data["kind"])
            status = RecordStatus(data.get("status", "active"))
        except ValueError as exc:
            raise RecordLoadError(f"{where}: {exc}") from None

        identity = Identity.from_dict(data["identity"], where=f"{where}.identity")
        capabilities = _string_list(data["capabilities"], key="capabilities", where=where)
        data_classes = _string_list(data["data_classes"], key="data_classes", where=where)
        expires = parse_expiry(data.get("expires"), where=f"{where}.expires", error=RecordLoadError)
        try:
            return cls(
                name=data["name"],
                kind=kind,
                version=data["version"],
                endpoint=data["endpoint"],
                identity=identity,
                schema_hash=data["schema_hash"],
                capabilities=capabilities,
                data_classes=data_classes,
                owner=data["owner"],
                status=status,
                expires=expires,
                ttl_seconds=data.get("ttl_seconds", 300),
                signature=signature,
                signature_algorithm=str(data.get("signature_algorithm", "ed25519")),
            )
        except RecordLoadError as exc:
            raise RecordLoadError(f"{where}: {exc}") from None

    @classmethod
    def from_agent_card(
        cls,
        card: Mapping[str, Any],
        *,
        owner: str,
        expires: datetime | None,
        identity: Identity,
        data_classes: tuple[str, ...],
    ) -> NameRecord:
        """Import an A2A Agent Card as an unsigned agent record.

        A card carries a name, URL, version, and skills. It does not say who owns the agent,
        when its authority should lapse, who vouches for it, or what data it touches, so the
        caller must say so. Nothing is guessed. ``expires=None`` is an explicit choice of no
        expiry. Capability names come from each skill's ``id`` (falling back to ``name``).
        ``schema_hash`` is the SHA-256 of the card as imported, so a changed card is a
        changed record. The result is unsigned; sign it with ``sign_record``.

        Raises:
            ValueError: If the card lacks a name, url, version, or usable skill, or the
                caller supplies an empty owner or an identity with no signer or fingerprint.
        """
        if not owner:
            raise ValueError("owner is required when importing an agent card")
        if not identity.signed_by or not identity.public_key_fingerprint:
            raise ValueError("identity with signed_by and public_key_fingerprint is required")
        missing = [key for key in ("name", "url", "version") if not card.get(key)]
        if missing:
            raise ValueError(f"agent card is missing required field(s): {', '.join(missing)}")

        capabilities: list[str] = []
        for skill in card.get("skills", []):
            if isinstance(skill, str):
                skill_name: Any = skill
            elif isinstance(skill, dict):
                skill_name = skill.get("id") or skill.get("name")
            else:
                skill_name = None
            if not skill_name:
                raise ValueError(f"agent card skill has neither 'id' nor 'name': {skill!r}")
            capabilities.append(str(skill_name))

        card_bytes = json.dumps(card, sort_keys=True, separators=(",", ":"), default=str).encode()
        return cls(
            name=str(card["name"]),
            kind=RecordKind.AGENT,
            version=str(card["version"]),
            endpoint=str(card["url"]),
            identity=identity,
            schema_hash=f"sha256:{hashlib.sha256(card_bytes).hexdigest()}",
            capabilities=tuple(capabilities),
            data_classes=data_classes,
            owner=owner,
            expires=expires,
        )


@dataclass(frozen=True)
class RecordInfo:
    """A summary of a stored record. ``status`` is the effective lifecycle status, which
    includes operator revocation, and ``verification`` is computed by the verifier."""

    name: str
    kind: RecordKind
    version: str
    status: RecordStatus
    owner: str
    fingerprint: str
    verification: VerificationStatus


def _load_file(path: Path) -> Any:
    if not path.exists():
        raise RecordLoadError(f"Records file not found: {path}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RecordLoadError(f"{path}: cannot parse: {exc}") from exc


def load_records_file(path: str | Path) -> list[NameRecord]:
    """Load records from a YAML or JSON file.

    The file holds a list of records, a ``records:`` list, or a single record mapping.

    Raises:
        RecordLoadError: If the file is missing, unparseable, or any record is invalid.
            Messages name the file and the record's position.
    """
    file_path = Path(path)
    data = _load_file(file_path)
    if data is None:
        return []
    if isinstance(data, dict) and "records" in data and len(data) == 1:
        data = data["records"]
    items = data if isinstance(data, list) else [data]
    records: list[NameRecord] = []
    for index, item in enumerate(items):
        where = f"{file_path}: record[{index}]"
        if not isinstance(item, dict):
            raise RecordLoadError(f"{where}: expected a mapping, got {type(item).__name__}")
        records.append(NameRecord.from_dict(item, where=where))
    return records


def load_records_directory(path: str | Path) -> list[NameRecord]:
    """Recursively load every ``.yaml``, ``.yml``, and ``.json`` file under a directory."""
    directory = Path(path)
    if not directory.is_dir():
        raise RecordLoadError(f"Records directory not found: {directory}")
    files = sorted(f for ext in ("*.yaml", "*.yml", "*.json") for f in directory.rglob(ext))
    return [record for file in files for record in load_records_file(file)]
