"""SemanticMemory: vector-indexed long-term store (Protocol + in-memory TF-IDF impl)."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from pyagent_context.item import ContextItem


@dataclass(frozen=True)
class SearchResult:
    """Result of a semantic search.

    Attributes:
        item: The matching context item.
        score: Relevance score (0.0–1.0).
    """

    item: ContextItem
    score: float


@runtime_checkable
class SemanticMemoryProtocol(Protocol):
    """Interface for any vector-backed semantic memory store."""

    def add(self, item: ContextItem) -> None:
        """Index an item for later retrieval."""
        ...

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Find the most relevant items for a query."""
        ...

    def remove(self, item_id: str) -> bool:
        """Remove an item by ID. Returns True if found."""
        ...

    def clear(self) -> None:
        """Remove all items."""
        ...

    def __len__(self) -> int: ...


class InMemorySemanticStore:
    """In-memory semantic store using TF-IDF cosine similarity.

    No external dependencies — suitable for testing and small datasets.
    For production, use a vector DB adapter (ChromaDB, Pinecone, etc.).

    Args:
        stop_words: Optional set of words to ignore in scoring.
    """

    def __init__(self, stop_words: set[str] | None = None) -> None:
        self._items: dict[str, ContextItem] = {}
        self._tf_cache: dict[str, dict[str, float]] = {}
        self._stop_words = stop_words or {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "and",
            "but", "or", "nor", "not", "so", "yet", "both", "either",
            "neither", "each", "every", "all", "any", "few", "more",
            "most", "other", "some", "such", "no", "only", "own", "same",
            "than", "too", "very", "just", "because", "about", "between",
            "it", "its", "this", "that", "these", "those", "i", "me",
            "my", "we", "our", "you", "your", "he", "him", "his", "she",
            "her", "they", "them", "their", "what", "which", "who",
        }

    def add(self, item: ContextItem) -> None:
        self._items[item.id] = item
        self._tf_cache[item.id] = self._compute_tf(item.content)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if not self._items:
            return []

        query_tf = self._compute_tf(query)
        idf = self._compute_idf()

        query_tfidf = {w: tf * idf.get(w, 0.0) for w, tf in query_tf.items()}

        results: list[SearchResult] = []
        for item_id, item in self._items.items():
            doc_tf = self._tf_cache.get(item_id, {})
            doc_tfidf = {w: tf * idf.get(w, 0.0) for w, tf in doc_tf.items()}
            score = self._cosine_similarity(query_tfidf, doc_tfidf)
            if score > 0:
                results.append(SearchResult(item=item, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def remove(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            self._tf_cache.pop(item_id, None)
            return True
        return False

    def clear(self) -> None:
        self._items.clear()
        self._tf_cache.clear()

    def __len__(self) -> int:
        return len(self._items)

    # ------------------------------------------------------------------
    # TF-IDF helpers
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        words = text.lower().split()
        return [w.strip(".,!?;:\"'()[]{}") for w in words if w.strip(".,!?;:\"'()[]{}") not in self._stop_words]

    def _compute_tf(self, text: str) -> dict[str, float]:
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = len(tokens)
        return {word: count / total for word, count in counts.items()}

    def _compute_idf(self) -> dict[str, float]:
        n_docs = len(self._items)
        if n_docs == 0:
            return {}
        doc_freq: Counter[str] = Counter()
        for tf in self._tf_cache.values():
            for word in tf:
                doc_freq[word] += 1
        return {word: math.log(n_docs / (1 + freq)) for word, freq in doc_freq.items()}

    @staticmethod
    def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common_keys = set(a) & set(b)
        if not common_keys:
            return 0.0
        dot = sum(a[k] * b[k] for k in common_keys)
        mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)
