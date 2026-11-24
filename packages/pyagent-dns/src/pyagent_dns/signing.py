"""Ed25519 signing and verification of NameRecords, and the trusted keys they verify against."""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from pyagent_dns.records import check_keys

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from pyagent_dns.records import NameRecord

ALGORITHM = "ed25519"
SIGNING_KEY_ENV = "PYAGENT_DNS_SIGNING_KEY"


class VerificationStatus(StrEnum):
    """Outcome of checking a record's signature. Computed by the verifier, never read from a file.

    ``UNVERIFIED`` means nothing was proven false: the record is unsigned, its signer is not
    trusted, or it pins a key this reader does not trust. ``FAILED`` means a trusted key was
    found and the signature does not match, which is a stronger and more alarming result.
    """

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


class TrustedKeysError(ValueError):
    """Raised when a trusted key or trusted keys file is malformed."""


def _parse_public_key(public_key: str) -> ed25519.Ed25519PublicKey:
    """Parse an Ed25519 public key given as PEM or as base64 of the 32 raw bytes."""
    text = public_key.strip()
    if text.startswith("-----BEGIN"):
        key = serialization.load_pem_public_key(text.encode())
        if not isinstance(key, ed25519.Ed25519PublicKey):
            raise ValueError("only Ed25519 public keys are supported")
        return key
    raw = base64.b64decode(text, validate=True)
    if len(raw) != 32:
        raise ValueError(f"an Ed25519 public key is 32 bytes, got {len(raw)}")
    return ed25519.Ed25519PublicKey.from_public_bytes(raw)


def fingerprint_of_public_key(public_key: str) -> str:
    """Return ``sha256:`` plus the hex digest of the key's 32 raw bytes.

    Args:
        public_key: PEM text, or base64 of the raw key.
    """
    raw = _parse_public_key(public_key).public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


@dataclass(frozen=True)
class TrustedKey:
    """A public key this reader trusts a named signer to sign with.

    The declared fingerprint is checked against the key material on construction. A
    fingerprint that merely claims to match would let a records file pin one key while
    verification used another.

    Args:
        signer: Signer name, matching ``Identity.signed_by`` on records.
        public_key_fingerprint: ``sha256:`` plus the hex digest of the key.
        public_key: The key, PEM or base64 raw Ed25519.

    Raises:
        TrustedKeysError: If a field is empty, the key does not parse, or the fingerprint
            does not match the key.
    """

    signer: str
    public_key_fingerprint: str
    public_key: str

    def __post_init__(self) -> None:
        if not self.signer:
            raise TrustedKeysError("trusted key has an empty signer")
        try:
            actual = fingerprint_of_public_key(self.public_key)
        except ValueError as exc:
            raise TrustedKeysError(f"trusted key for '{self.signer}' is not usable: {exc}") from exc
        if actual != self.public_key_fingerprint:
            raise TrustedKeysError(
                f"trusted key for '{self.signer}' declares fingerprint "
                f"{self.public_key_fingerprint} but the key's fingerprint is {actual}"
            )


class TrustedKeys:
    """The set of public keys a reader trusts, grouped by signer.

    A signer may hold several keys at once, which is what lets a key rotation overlap.
    """

    def __init__(self, keys: Iterable[TrustedKey] = ()) -> None:
        self._keys = list(keys)

    def get(self, signer: str) -> list[TrustedKey]:
        """Return every trusted key for ``signer``."""
        return [key for key in self._keys if key.signer == signer]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, where: str = "trusted keys") -> TrustedKeys:
        """Build from ``{"keys": [{"signer", "public_key_fingerprint", "public_key"}, ...]}``.

        Raises:
            TrustedKeysError: On a missing or unknown key, or a key that fails validation.
        """
        check_keys(data, required=["keys"], optional=[], where=where, error=TrustedKeysError)
        entries = data["keys"]
        if not isinstance(entries, list):
            raise TrustedKeysError(f"{where}: 'keys' must be a list")
        keys: list[TrustedKey] = []
        for index, entry in enumerate(entries):
            entry_where = f"{where}: keys[{index}]"
            if not isinstance(entry, dict):
                raise TrustedKeysError(f"{entry_where}: expected a mapping")
            check_keys(
                entry,
                required=["signer", "public_key_fingerprint", "public_key"],
                optional=[],
                where=entry_where,
                error=TrustedKeysError,
            )
            if not all(isinstance(value, str) for value in entry.values()):
                raise TrustedKeysError(f"{entry_where}: every field must be a string")
            try:
                keys.append(TrustedKey(**entry))
            except TrustedKeysError as exc:
                raise TrustedKeysError(f"{entry_where}: {exc}") from None
        return cls(keys)

    @classmethod
    def from_file(cls, path: str | Path) -> TrustedKeys:
        """Load a YAML or JSON trusted keys file.

        Raises:
            FileNotFoundError: If the file does not exist.
            TrustedKeysError: If the file is unparseable or any key is invalid.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Trusted keys file not found: {file_path}")
        try:
            data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise TrustedKeysError(f"{file_path}: cannot parse: {exc}") from exc
        if not isinstance(data, dict):
            raise TrustedKeysError(f"{file_path}: expected a mapping with a 'keys' list")
        return cls.from_dict(data, where=str(file_path))


def generate_keypair(directory: str | Path) -> tuple[Path, Path]:
    """Write a new Ed25519 keypair to ``private_key.pem`` and ``public_key.pem``.

    The private key is created with mode 0600 from the start, so it is never briefly
    readable by other users, and it is unencrypted PKCS8: passphrases are not supported in
    0.1. Existing key files are never overwritten, because overwriting a key that has
    signed records would orphan them.

    Raises:
        FileExistsError: If either file already exists.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    private_path, public_path = directory / "private_key.pem", directory / "public_key.pem"
    for path in (private_path, public_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing key file: {path}")

    private_key = ed25519.Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    descriptor = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(private_pem)
    with public_path.open("xb") as handle:
        handle.write(public_pem)
    return private_path, public_path


def load_private_key(path: str | Path | None = None) -> ed25519.Ed25519PrivateKey:
    """Load an unencrypted PKCS8 Ed25519 private key.

    Args:
        path: Key file. If omitted, the path is read from ``PYAGENT_DNS_SIGNING_KEY``. The
            variable holds a path, never key material, which would leak into process
            listings and CI logs.

    Raises:
        ValueError: If no path is given, the key is encrypted, or it is not Ed25519.
        FileNotFoundError: If the file does not exist.
    """
    if path is None:
        path = os.environ.get(SIGNING_KEY_ENV)
        if not path:
            raise ValueError(f"No private key path given and {SIGNING_KEY_ENV} is not set")
    key_path = Path(path)
    if not key_path.exists():
        raise FileNotFoundError(f"Private key file not found: {key_path}")
    try:
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    except TypeError as exc:
        raise ValueError(
            f"{key_path} is passphrase-protected; passphrases are not supported in 0.1"
        ) from exc
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise ValueError(f"{key_path} is not an Ed25519 private key")
    return key


def sign_record(record: NameRecord, private_key: ed25519.Ed25519PrivateKey) -> NameRecord:
    """Return a copy of ``record`` signed over its canonical bytes.

    ``signature_algorithm`` is set before the bytes are taken, so the signature covers the
    record exactly as returned.
    """
    prepared = dataclasses.replace(record, signature=None, signature_algorithm=ALGORITHM)
    signature = base64.b64encode(private_key.sign(prepared.canonical_bytes())).decode("ascii")
    return dataclasses.replace(prepared, signature=signature)


def verify_record(record: NameRecord, trusted_keys: TrustedKeys) -> VerificationStatus:
    """Verify a record's signature against the trusted keys for its signer.

    The key used is always the trusted one. A public key carried inside the record is
    ignored, so a record cannot vouch for itself.

    Returns:
        ``VERIFIED`` if a trusted key whose fingerprint the record pins verifies the
        signature. ``UNVERIFIED`` if the record is unsigned, uses an unsupported
        algorithm, or its signer or pinned fingerprint is not trusted. ``FAILED`` if a
        matching trusted key is found and the signature does not verify.
    """
    if not record.signature or record.signature_algorithm != ALGORITHM:
        return VerificationStatus.UNVERIFIED
    pinned = record.identity.public_key_fingerprint
    trusted = next(
        (
            key
            for key in trusted_keys.get(record.identity.signed_by)
            if key.public_key_fingerprint == pinned
        ),
        None,
    )
    if trusted is None:
        return VerificationStatus.UNVERIFIED
    try:
        signature = base64.b64decode(record.signature, validate=True)
        _parse_public_key(trusted.public_key).verify(signature, record.canonical_bytes())
    except (InvalidSignature, ValueError):
        return VerificationStatus.FAILED
    return VerificationStatus.VERIFIED
