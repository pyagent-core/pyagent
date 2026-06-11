"""Tests for ContextLifecycle: expiry sweep, freshness decay, consolidation."""

from __future__ import annotations

import time

from pyagent_context.item import ContextItem, TrustLevel
from pyagent_context.ledger import ContextLedger
from pyagent_context.lifecycle import ContextLifecycle


def test_sweep_expired() -> None:
    ledger = ContextLedger()
    ledger.append(ContextItem(content="expired", source="s", expires_at=time.time() - 10))
    ledger.append(ContextItem(content="active", source="s"))
    ledger.append(ContextItem(content="future", source="s", expires_at=time.time() + 3600))

    lifecycle = ContextLifecycle()
    new_ledger, expired = lifecycle.sweep_expired(ledger)

    assert len(expired) == 1
    assert expired[0].content == "expired"
    assert len(new_ledger) == 2


def test_freshness_decay() -> None:
    ledger = ContextLedger()
    # Old item: 2 hours ago
    ledger.append(
        ContextItem(
            content="old item",
            source="s",
            timestamp=time.time() - 7200,
            token_estimate=100,
        )
    )
    # New item: just now
    ledger.append(
        ContextItem(
            content="new item",
            source="s",
            timestamp=time.time(),
            token_estimate=100,
        )
    )

    lifecycle = ContextLifecycle()
    decayed = lifecycle.apply_freshness_decay(ledger, half_life_seconds=3600)

    items = decayed.items
    # Old item should have much lower tokens than new
    assert items[0].token_estimate < items[1].token_estimate
    # New item should be close to original
    assert items[1].token_estimate >= 90  # small decay from milliseconds


def test_consolidation() -> None:
    ledger = ContextLedger()
    # Two similar items from same source
    ledger.append(
        ContextItem(
            content="Python asyncio patterns for concurrency",
            source="researcher",
            trust_level=TrustLevel.INFERRED,
        )
    )
    ledger.append(
        ContextItem(
            content="Python asyncio patterns for parallel tasks",
            source="researcher",
            trust_level=TrustLevel.VERIFIED,
        )
    )
    # Different source
    ledger.append(
        ContextItem(
            content="JavaScript React hooks",
            source="frontend_agent",
        )
    )

    lifecycle = ContextLifecycle(consolidation_threshold=0.4)
    consolidated = lifecycle.consolidate(ledger)

    # The two similar Python items should merge into one
    researcher_items = [i for i in consolidated.items if i.source == "researcher"]
    assert len(researcher_items) == 1
    # Merged item should have highest trust
    assert researcher_items[0].trust_level == TrustLevel.VERIFIED
    # JavaScript item stays separate
    frontend_items = [i for i in consolidated.items if i.source == "frontend_agent"]
    assert len(frontend_items) == 1


def test_consolidation_no_merge_different_content() -> None:
    ledger = ContextLedger()
    ledger.append(ContextItem(content="Python web framework", source="agent"))
    ledger.append(ContextItem(content="Quantum computing algorithms", source="agent"))

    lifecycle = ContextLifecycle(consolidation_threshold=0.6)
    consolidated = lifecycle.consolidate(ledger)

    # Totally different content should not merge
    assert len(consolidated) == 2
