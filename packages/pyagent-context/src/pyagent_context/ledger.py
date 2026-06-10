"""ContextLedger: append-only log of ContextItems with query, conversion, and snapshot."""

from __future__ import annotations

import time
from typing import Any

from pyagent_patterns.base import Message
from pyagent_context.item import ContextItem, TrustLevel, TRUST_ORDER


class ContextLedger:
    """Append-only ledger of context items.

    Supports querying by trust level, age, and source. Converts items
    to ``Message`` lists for use with patterns.

    Args:
        items: Optional initial items.
    """

    def __init__(self, items: list[ContextItem] | None = None) -> None:
        self._items: list[ContextItem] = list(items) if items else []

    def append(self, item: ContextItem) -> None:
        """Add an item to the ledger."""
        self._items.append(item)

    def add(
        self,
        content: str,
        source: str,
        trust_level: TrustLevel = TrustLevel.INFERRED,
        **kwargs: Any,
    ) -> ContextItem:
        """Create and append a new item in one step.

        Returns:
            The created ``ContextItem``.
        """
        item = ContextItem(content=content, source=source, trust_level=trust_level, **kwargs)
        self._items.append(item)
        return item

    def query(
        self,
        *,
        min_trust: TrustLevel | None = None,
        max_age_seconds: float | None = None,
        source: str | None = None,
    ) -> list[ContextItem]:
        """Filter items by trust level, age, and/or source.

        Args:
            min_trust: Only return items at or above this trust level.
            max_age_seconds: Only return items newer than this.
            source: Only return items from this source.

        Returns:
            Filtered list of items (chronological order).
        """
        now = time.time()
        results: list[ContextItem] = []
        for item in self._items:
            if min_trust is not None and TRUST_ORDER.get(item.trust_level, 0) < TRUST_ORDER.get(min_trust, 0):
                continue
            if max_age_seconds is not None and (now - item.timestamp) > max_age_seconds:
                continue
            if source is not None and item.source != source:
                continue
            results.append(item)
        return results

    @property
    def total_tokens(self) -> int:
        """Sum of token estimates across all items."""
        return sum(item.token_estimate for item in self._items)

    def to_messages(self, max_tokens: int | None = None) -> list[Message]:
        """Convert ledger items to a list of Messages.

        If ``max_tokens`` is set, include items from most recent backward
        until the budget is exhausted.

        Args:
            max_tokens: Optional token budget.

        Returns:
            List of ``Message`` objects.
        """
        if max_tokens is None:
            return [
                Message.assistant(item.content, name=item.source)
                for item in self._items
            ]

        # Walk backward, accumulate until budget exhausted
        selected: list[ContextItem] = []
        budget = max_tokens
        for item in reversed(self._items):
            if item.token_estimate <= budget:
                selected.append(item)
                budget -= item.token_estimate
            else:
                break

        selected.reverse()
        return [Message.assistant(item.content, name=item.source) for item in selected]

    def snapshot(self) -> dict:
        """Serialize the full ledger to a JSON-compatible dict."""
        return {
            "items": [item.to_dict() for item in self._items],
            "total_tokens": self.total_tokens,
            "count": len(self._items),
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> ContextLedger:
        """Restore a ledger from a snapshot dict."""
        items = [ContextItem.from_dict(d) for d in data["items"]]
        return cls(items=items)

    @property
    def items(self) -> list[ContextItem]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return len(self._items) > 0

    def clear(self) -> None:
        """Remove all items."""
        self._items.clear()
