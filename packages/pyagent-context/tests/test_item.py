"""Tests for ContextItem: create, serialize, token estimate, expiry."""

from __future__ import annotations

import time

from pyagent_context.item import ContextItem, Sensitivity, TrustLevel


def test_create_default() -> None:
    item = ContextItem(content="Hello world", source="user")
    assert item.content == "Hello world"
    assert item.source == "user"
    assert item.trust_level == TrustLevel.INFERRED
    assert item.sensitivity == Sensitivity.INTERNAL
    assert item.expires_at is None
    assert item.derived_from is None
    assert len(item.id) == 12


def test_token_estimate_auto() -> None:
    item = ContextItem(content="a" * 100, source="test")
    assert item.token_estimate == 25  # 100 // 4


def test_token_estimate_explicit() -> None:
    item = ContextItem(content="hello", source="test", token_estimate=99)
    assert item.token_estimate == 99


def test_is_expired_never() -> None:
    item = ContextItem(content="x", source="s")
    assert not item.is_expired


def test_is_expired_past() -> None:
    item = ContextItem(content="x", source="s", expires_at=time.time() - 10)
    assert item.is_expired


def test_is_expired_future() -> None:
    item = ContextItem(content="x", source="s", expires_at=time.time() + 3600)
    assert not item.is_expired


def test_serialize_roundtrip() -> None:
    item = ContextItem(
        content="Important fact",
        source="analyst",
        trust_level=TrustLevel.VERIFIED,
        sensitivity=Sensitivity.CONFIDENTIAL,
        expires_at=time.time() + 3600,
        derived_from="abc123",
    )
    data = item.to_dict()
    restored = ContextItem.from_dict(data)

    assert restored.id == item.id
    assert restored.content == item.content
    assert restored.source == item.source
    assert restored.trust_level == TrustLevel.VERIFIED
    assert restored.sensitivity == Sensitivity.CONFIDENTIAL
    assert restored.derived_from == "abc123"


def test_trust_ordering() -> None:
    assert TrustLevel.VERIFIED > TrustLevel.USER_PROVIDED
    assert TrustLevel.USER_PROVIDED > TrustLevel.EXTERNAL
    assert TrustLevel.EXTERNAL > TrustLevel.INFERRED
    assert TrustLevel.INFERRED <= TrustLevel.VERIFIED
