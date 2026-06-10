"""Tests for ContextLedger: append, query, total_tokens, to_messages, snapshot."""

from __future__ import annotations

import time

from pyagent_context.item import ContextItem, TrustLevel
from pyagent_context.ledger import ContextLedger


def _make_item(content: str, source: str = "agent", trust: TrustLevel = TrustLevel.INFERRED, age: float = 0.0) -> ContextItem:
    return ContextItem(
        content=content,
        source=source,
        trust_level=trust,
        timestamp=time.time() - age,
    )


def test_append_and_len() -> None:
    ledger = ContextLedger()
    assert len(ledger) == 0
    ledger.append(_make_item("hello"))
    assert len(ledger) == 1


def test_add_convenience() -> None:
    ledger = ContextLedger()
    item = ledger.add("test content", "agent_1", TrustLevel.VERIFIED)
    assert item.content == "test content"
    assert len(ledger) == 1


def test_query_by_trust() -> None:
    ledger = ContextLedger()
    ledger.append(_make_item("low trust", trust=TrustLevel.INFERRED))
    ledger.append(_make_item("high trust", trust=TrustLevel.VERIFIED))

    results = ledger.query(min_trust=TrustLevel.VERIFIED)
    assert len(results) == 1
    assert results[0].trust_level == TrustLevel.VERIFIED


def test_query_by_age() -> None:
    ledger = ContextLedger()
    ledger.append(_make_item("old", age=7200))  # 2 hours ago
    ledger.append(_make_item("new", age=60))     # 1 minute ago

    results = ledger.query(max_age_seconds=3600)
    assert len(results) == 1
    assert results[0].content == "new"


def test_query_by_source() -> None:
    ledger = ContextLedger()
    ledger.append(_make_item("from a", source="agent_a"))
    ledger.append(_make_item("from b", source="agent_b"))

    results = ledger.query(source="agent_a")
    assert len(results) == 1
    assert results[0].source == "agent_a"


def test_total_tokens() -> None:
    ledger = ContextLedger()
    ledger.append(ContextItem(content="a" * 100, source="s"))  # 25 tokens
    ledger.append(ContextItem(content="b" * 200, source="s"))  # 50 tokens
    assert ledger.total_tokens == 75


def test_to_messages_all() -> None:
    ledger = ContextLedger()
    ledger.append(_make_item("msg1", source="agent_a"))
    ledger.append(_make_item("msg2", source="agent_b"))

    msgs = ledger.to_messages()
    assert len(msgs) == 2
    assert msgs[0].content == "msg1"
    assert msgs[0].name == "agent_a"


def test_to_messages_budget() -> None:
    ledger = ContextLedger()
    ledger.append(ContextItem(content="a" * 400, source="s", token_estimate=100))
    ledger.append(ContextItem(content="b" * 400, source="s", token_estimate=100))
    ledger.append(ContextItem(content="c" * 400, source="s", token_estimate=100))

    msgs = ledger.to_messages(max_tokens=200)
    assert len(msgs) == 2  # last two items fit in 200 tokens


def test_snapshot_roundtrip() -> None:
    ledger = ContextLedger()
    ledger.append(_make_item("fact 1", source="analyst", trust=TrustLevel.VERIFIED))
    ledger.append(_make_item("fact 2", source="researcher"))

    snap = ledger.snapshot()
    assert snap["count"] == 2

    restored = ContextLedger.from_snapshot(snap)
    assert len(restored) == 2
    assert restored.items[0].content == "fact 1"
    assert restored.items[0].trust_level == TrustLevel.VERIFIED


def test_clear() -> None:
    ledger = ContextLedger()
    ledger.append(_make_item("x"))
    ledger.clear()
    assert len(ledger) == 0
