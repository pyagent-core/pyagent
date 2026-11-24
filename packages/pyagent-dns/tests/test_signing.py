"""Tests for canonical signing, verification, trusted keys, and key files."""

from __future__ import annotations

import base64
import dataclasses
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from pyagent_dns.records import Identity, RecordStatus
from pyagent_dns.signing import (
    SIGNING_KEY_ENV,
    TrustedKey,
    TrustedKeys,
    TrustedKeysError,
    VerificationStatus,
    fingerprint_of_public_key,
    generate_keypair,
    load_private_key,
    sign_record,
    verify_record,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyagent_dns.records import NameRecord

FIXTURES = Path(__file__).parent / "fixtures"
VERIFIED, UNVERIFIED, FAILED = (
    VerificationStatus.VERIFIED,
    VerificationStatus.UNVERIFIED,
    VerificationStatus.FAILED,
)


# -- Verification ----------------------------------------------------------------------------


def test_a_cleanly_signed_record_verifies(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys
) -> None:
    assert verify_record(make_record(), trusted_keys) == VERIFIED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("endpoint", "https://malicious.example/endpoint"),
        ("schema_hash", "sha256:" + "00" * 32),
        ("capabilities", ("read_positions", "unauthorized_admin_drop")),
        ("expires", datetime(2099, 1, 1, tzinfo=UTC)),
        ("data_classes", ("public",)),
        ("status", RecordStatus.DEPRECATED),
        ("owner", "attacker"),
        ("version", "9.9.9"),
        ("ttl_seconds", 86400),
    ],
)
def test_altering_any_signed_field_after_signing_fails_verification(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys, field: str, value: Any
) -> None:
    """Each field is a different attack: redirect, swap the schema, widen scope, extend life..."""
    altered = dataclasses.replace(make_record(), **{field: value})
    assert verify_record(altered, trusted_keys) == FAILED


def test_the_signature_is_not_part_of_what_is_signed(
    make_record: Callable[..., NameRecord],
    trusted_keys: TrustedKeys,
    private_key: ed25519.Ed25519PrivateKey,
) -> None:
    once = make_record()
    twice = sign_record(once, private_key)
    assert twice.signature == once.signature  # Ed25519 is deterministic
    assert verify_record(twice, trusted_keys) == VERIFIED


def test_an_unsigned_record_is_unverified_not_failed(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys
) -> None:
    assert verify_record(make_record(sign=False), trusted_keys) == UNVERIFIED


def test_an_unknown_signer_is_unverified(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys
) -> None:
    record = make_record()
    rogue = dataclasses.replace(
        record, identity=dataclasses.replace(record.identity, signed_by="rogue")
    )
    assert verify_record(rogue, trusted_keys) == UNVERIFIED


def test_pinning_a_key_the_reader_does_not_trust_is_unverified_not_failed(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys
) -> None:
    """Nothing is proven false: the reader just has no basis for trust."""
    record = make_record()
    pinned_elsewhere = dataclasses.replace(
        record,
        identity=dataclasses.replace(record.identity, public_key_fingerprint="sha256:" + "99" * 32),
    )
    assert verify_record(pinned_elsewhere, trusted_keys) == UNVERIFIED


def test_a_record_cannot_vouch_for_itself_by_carrying_its_own_key(
    tmp_path: Path,
    make_record: Callable[..., NameRecord],
    trusted_keys: TrustedKeys,
    signer_name: str,
    public_key_fingerprint: str,
) -> None:
    """An attacker signs with their own key and claims the trusted signer and the trusted pin.
    Verification uses the trusted key, so the signature does not match: FAILED."""
    attacker_private, attacker_public = generate_keypair(tmp_path / "attacker")
    forged = make_record(sign=False)
    forged = dataclasses.replace(
        forged,
        identity=Identity(
            public_key_fingerprint=public_key_fingerprint,  # the trusted pin
            public_key=attacker_public.read_text(),  # but the attacker's key travels in the record
            signed_by=signer_name,
        ),
    )
    forged = sign_record(forged, load_private_key(attacker_private))
    assert verify_record(forged, trusted_keys) == FAILED


def test_an_attacker_pinning_their_own_fingerprint_is_simply_untrusted(
    tmp_path: Path,
    make_record: Callable[..., NameRecord],
    trusted_keys: TrustedKeys,
    signer_name: str,
) -> None:
    attacker_private, attacker_public = generate_keypair(tmp_path / "attacker")
    pem = attacker_public.read_text()
    forged = dataclasses.replace(
        make_record(sign=False),
        identity=Identity(fingerprint_of_public_key(pem), pem, signed_by=signer_name),
    )
    forged = sign_record(forged, load_private_key(attacker_private))
    assert verify_record(forged, trusted_keys) == UNVERIFIED


def test_an_unsupported_signature_algorithm_is_unverified(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys
) -> None:
    record = dataclasses.replace(make_record(), signature_algorithm="rsa-sha256")
    assert verify_record(record, trusted_keys) == UNVERIFIED


def test_signing_covers_the_record_exactly_as_returned(
    make_record: Callable[..., NameRecord],
    trusted_keys: TrustedKeys,
    private_key: ed25519.Ed25519PrivateKey,
) -> None:
    """A record built with another algorithm label is signed as ed25519, over those bytes."""
    odd = dataclasses.replace(make_record(sign=False), signature_algorithm="none")
    signed = sign_record(odd, private_key)
    assert signed.signature_algorithm == "ed25519"
    assert verify_record(signed, trusted_keys) == VERIFIED


@pytest.mark.parametrize(
    "junk", ["not base64 at all!!", "QUJD", base64.b64encode(b"x" * 64).decode()]
)
def test_a_malformed_or_wrong_signature_fails_cleanly(
    make_record: Callable[..., NameRecord], trusted_keys: TrustedKeys, junk: str
) -> None:
    record = dataclasses.replace(make_record(), signature=junk)
    assert verify_record(record, trusted_keys) == FAILED


def test_rotation_overlap_two_trusted_keys_for_one_signer(
    tmp_path: Path,
    make_record: Callable[..., NameRecord],
    trusted_keys: TrustedKeys,
    signer_name: str,
) -> None:
    private_path, public_path = generate_keypair(tmp_path / "second")
    pem = public_path.read_text()
    second = fingerprint_of_public_key(pem)
    old_record = make_record("old.tool")
    new_record = sign_record(
        dataclasses.replace(
            make_record("new.tool", sign=False),
            identity=Identity(second, pem, signed_by=signer_name),
        ),
        load_private_key(private_path),
    )
    overlap = TrustedKeys([*trusted_keys.get(signer_name), TrustedKey(signer_name, second, pem)])
    assert verify_record(old_record, overlap) == VERIFIED
    assert verify_record(new_record, overlap) == VERIFIED
    assert verify_record(new_record, trusted_keys) == UNVERIFIED  # before the new key was trusted


# -- Trusted keys ----------------------------------------------------------------------------


def test_a_trusted_key_whose_fingerprint_does_not_match_its_key_is_rejected(
    public_key_pem: str,
) -> None:
    """Otherwise a records file could pin one key while verification used another."""
    with pytest.raises(TrustedKeysError, match="declares fingerprint"):
        TrustedKey("signer", "sha256:" + "00" * 32, public_key_pem)


@pytest.mark.parametrize(
    "bad_key",
    ["", "not a key", base64.b64encode(b"short").decode(), "!!!!"],
)
def test_a_trusted_key_that_is_not_an_ed25519_key_is_rejected(bad_key: str) -> None:
    with pytest.raises(TrustedKeysError, match="not usable"):
        TrustedKey("signer", "sha256:" + "00" * 32, bad_key)


def test_an_rsa_public_key_is_not_a_usable_trusted_key() -> None:
    pem = (
        rsa.generate_private_key(65537, 2048)
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    with pytest.raises(TrustedKeysError, match="only Ed25519"):
        TrustedKey("signer", "sha256:" + "00" * 32, pem)


def test_a_trusted_key_needs_a_signer(public_key_pem: str, public_key_fingerprint: str) -> None:
    with pytest.raises(TrustedKeysError, match="empty signer"):
        TrustedKey("", public_key_fingerprint, public_key_pem)


def test_the_fingerprint_is_the_same_for_a_pem_and_its_raw_base64_form(public_key_pem: str) -> None:
    key = serialization.load_pem_public_key(public_key_pem.encode())
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)  # type: ignore[union-attr]
    assert fingerprint_of_public_key(base64.b64encode(raw).decode()) == fingerprint_of_public_key(
        public_key_pem
    )


def test_trusted_keys_load_from_a_file(
    tmp_path: Path, signer_name: str, public_key_pem: str, public_key_fingerprint: str
) -> None:
    path = tmp_path / "keys.yaml"
    path.write_text(
        "keys:\n"
        f"  - signer: {signer_name}\n    public_key_fingerprint: {public_key_fingerprint}\n"
        f"    public_key: |\n{''.join('      ' + line + chr(10) for line in public_key_pem.splitlines())}"
    )
    (key,) = TrustedKeys.from_file(path).get(signer_name)
    assert key.public_key_fingerprint == public_key_fingerprint


def test_the_committed_fixture_keys_load() -> None:
    (key,) = TrustedKeys.from_file(FIXTURES / "trusted_keys.yaml").get("platform_registry")
    assert key.public_key_fingerprint.startswith("sha256:")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({}, "missing required key.*keys"),
        ({"keys": [], "extra": 1}, "unknown key.*extra"),
        ({"keys": "nope"}, "'keys' must be a list"),
        ({"keys": ["nope"]}, "expected a mapping"),
        ({"keys": [{"signer": "s"}]}, "missing required key"),
        (
            {"keys": [{"signer": "s", "public_key_fingerprint": "f", "public_key": 5}]},
            "must be a string",
        ),
        (
            {"keys": [{"signer": "s", "public_key_fingerprint": "f", "public_key": "k", "x": 1}]},
            "unknown key",
        ),
    ],
)
def test_a_malformed_trusted_keys_structure_is_an_error(data: dict[str, Any], message: str) -> None:
    with pytest.raises(TrustedKeysError, match=message):
        TrustedKeys.from_dict(data)


def test_trusted_keys_file_errors(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        TrustedKeys.from_file(tmp_path / "missing.yaml")
    (tmp_path / "bad.yaml").write_text("a: [unclosed")
    with pytest.raises(TrustedKeysError, match="cannot parse"):
        TrustedKeys.from_file(tmp_path / "bad.yaml")
    (tmp_path / "list.yaml").write_text("- a\n")
    with pytest.raises(TrustedKeysError, match="expected a mapping"):
        TrustedKeys.from_file(tmp_path / "list.yaml")


# -- Key files -------------------------------------------------------------------------------


def test_generate_keypair_writes_a_private_key_only_the_owner_can_read(tmp_path: Path) -> None:
    private_path, public_path = generate_keypair(tmp_path / "keys")
    assert "BEGIN PRIVATE KEY" in private_path.read_text()
    assert "BEGIN PUBLIC KEY" in public_path.read_text()
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(private_path).st_mode) == 0o600


def test_generate_keypair_never_overwrites_an_existing_key(tmp_path: Path) -> None:
    """Overwriting a key that has signed records would orphan every one of them."""
    private_path, public_path = generate_keypair(tmp_path)
    original = private_path.read_bytes()
    with pytest.raises(FileExistsError, match=r"private_key\.pem"):
        generate_keypair(tmp_path)
    public_path.unlink()
    with pytest.raises(FileExistsError, match=r"private_key\.pem"):
        generate_keypair(tmp_path)
    assert private_path.read_bytes() == original


def test_load_private_key_from_a_path(tmp_path: Path) -> None:
    private_path, _ = generate_keypair(tmp_path)
    assert isinstance(load_private_key(private_path), ed25519.Ed25519PrivateKey)


def test_load_private_key_reads_a_path_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private_path, _ = generate_keypair(tmp_path)
    monkeypatch.setenv(SIGNING_KEY_ENV, str(private_path))
    assert isinstance(load_private_key(), ed25519.Ed25519PrivateKey)


def test_load_private_key_without_a_path_or_variable_says_which_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(SIGNING_KEY_ENV, raising=False)
    with pytest.raises(ValueError, match=SIGNING_KEY_ENV):
        load_private_key()


def test_load_private_key_rejects_missing_encrypted_and_non_ed25519_keys(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_private_key(tmp_path / "missing.pem")

    encrypted = tmp_path / "encrypted.pem"
    encrypted.write_bytes(
        ed25519.Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(b"secret"),
        )
    )
    with pytest.raises(ValueError, match="passphrase"):
        load_private_key(encrypted)

    rsa_key = tmp_path / "rsa.pem"
    rsa_key.write_bytes(
        rsa.generate_private_key(65537, 2048).private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    with pytest.raises(ValueError, match="not an Ed25519"):
        load_private_key(rsa_key)
