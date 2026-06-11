"""ContextLifecycle: expiration sweep, consolidation, and freshness decay."""

from __future__ import annotations

import time
from collections import defaultdict

from pyagent_context.item import ContextItem
from pyagent_context.ledger import ContextLedger


class ContextLifecycle:
    """Manage the lifecycle of context items.

    Provides:
    - **Expiry sweep**: remove items past their ``expires_at``.
    - **Freshness decay**: reduce token budgets for old items.
    - **Consolidation**: merge items from the same source with similar content.

    Args:
        consolidation_threshold: Minimum keyword overlap ratio (0.0-1.0)
            to consider two items similar enough to merge.
    """

    def __init__(self, consolidation_threshold: float = 0.6) -> None:
        self._consolidation_threshold = consolidation_threshold

    def sweep_expired(self, ledger: ContextLedger) -> tuple[ContextLedger, list[ContextItem]]:
        """Remove expired items from the ledger.

        Args:
            ledger: The context ledger.

        Returns:
            Tuple of (new ledger without expired items, list of expired items).
        """
        now = time.time()
        kept: list[ContextItem] = []
        expired: list[ContextItem] = []

        for item in ledger.items:
            if item.expires_at is not None and now > item.expires_at:
                expired.append(item)
            else:
                kept.append(item)

        return ContextLedger(items=kept), expired

    def apply_freshness_decay(
        self,
        ledger: ContextLedger,
        half_life_seconds: float = 3600.0,
        min_tokens: int = 1,
    ) -> ContextLedger:
        """Reduce token estimates based on age.

        Older items get smaller token budgets, making them less likely
        to survive compression. Items retain at least ``min_tokens``.

        Args:
            ledger: The context ledger.
            half_life_seconds: Seconds for token estimate to halve.
            min_tokens: Minimum token estimate after decay.

        Returns:
            New ledger with decayed token estimates.
        """
        import math

        now = time.time()
        new_items: list[ContextItem] = []

        for item in ledger.items:
            age = now - item.timestamp
            decay_factor = math.exp(-age / half_life_seconds) if half_life_seconds > 0 else 1.0
            decayed_tokens = max(min_tokens, int(item.token_estimate * decay_factor))

            new_item = ContextItem(
                content=item.content,
                source=item.source,
                timestamp=item.timestamp,
                trust_level=item.trust_level,
                sensitivity=item.sensitivity,
                expires_at=item.expires_at,
                derived_from=item.derived_from,
                token_estimate=decayed_tokens,
            )
            new_item._id = item.id
            new_items.append(new_item)

        return ContextLedger(items=new_items)

    def consolidate(self, ledger: ContextLedger) -> ContextLedger:
        """Merge similar items from the same source.

        When two items from the same source have high keyword overlap,
        they are merged into one with combined content and the higher
        trust level.

        Args:
            ledger: The context ledger.

        Returns:
            New ledger with consolidated items.
        """
        by_source: dict[str, list[ContextItem]] = defaultdict(list)
        for item in ledger.items:
            by_source[item.source].append(item)

        consolidated: list[ContextItem] = []

        for source, items in by_source.items():
            merged_indices: set[int] = set()

            for i, item_a in enumerate(items):
                if i in merged_indices:
                    continue
                merged_content = item_a.content
                best_trust = item_a.trust_level
                latest_time = item_a.timestamp

                for j in range(i + 1, len(items)):
                    if j in merged_indices:
                        continue
                    item_b = items[j]
                    if (
                        self._similarity(item_a.content, item_b.content)
                        >= self._consolidation_threshold
                    ):
                        merged_content = f"{merged_content}\n{item_b.content}"
                        if item_b.trust_level > best_trust:
                            best_trust = item_b.trust_level
                        latest_time = max(latest_time, item_b.timestamp)
                        merged_indices.add(j)

                new_item = ContextItem(
                    content=merged_content,
                    source=source,
                    timestamp=latest_time,
                    trust_level=best_trust,
                    sensitivity=item_a.sensitivity,
                    expires_at=item_a.expires_at,
                    derived_from=item_a.id,
                )
                consolidated.append(new_item)

        # Sort by timestamp to maintain chronological order
        consolidated.sort(key=lambda x: x.timestamp)
        return ContextLedger(items=consolidated)

    @staticmethod
    def _similarity(text_a: str, text_b: str) -> float:
        """Keyword overlap ratio (Jaccard-like)."""
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
