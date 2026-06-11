"""WorkingMemory: bounded deque with automatic eviction and token limit."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyagent_context.item import ContextItem


class WorkingMemory:
    """Bounded working memory for a single pattern run.

    Evicts the oldest items when capacity is exceeded (either by count
    or by total token estimate).

    Args:
        max_items: Maximum number of items to keep.
        max_tokens: Maximum total token estimate before eviction.
    """

    def __init__(
        self,
        max_items: int = 100,
        max_tokens: int = 50_000,
    ) -> None:
        self._max_items = max_items
        self._max_tokens = max_tokens
        self._items: deque[ContextItem] = deque()

    def add(self, item: ContextItem) -> list[ContextItem]:
        """Add an item, evicting oldest if necessary.

        Returns:
            List of evicted items (empty if none were evicted).
        """
        evicted: list[ContextItem] = []
        self._items.append(item)

        # Evict by count
        while len(self._items) > self._max_items:
            evicted.append(self._items.popleft())

        # Evict by token budget
        while self.total_tokens > self._max_tokens and len(self._items) > 1:
            evicted.append(self._items.popleft())

        return evicted

    @property
    def total_tokens(self) -> int:
        return sum(item.token_estimate for item in self._items)

    @property
    def items(self) -> list[ContextItem]:
        return list(self._items)

    @property
    def utilization(self) -> float:
        """Token utilization as a fraction of max_tokens."""
        return self.total_tokens / self._max_tokens if self._max_tokens > 0 else 0.0

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return len(self._items) > 0
