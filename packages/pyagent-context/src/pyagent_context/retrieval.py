"""TrustAwareRetriever: score candidates by trust × recency × relevance."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from pyagent_context.item import ContextItem, TRUST_ORDER
from pyagent_context.ledger import ContextLedger


@dataclass(frozen=True)
class ScoredItem:
    """A context item with a composite retrieval score.

    Attributes:
        item: The context item.
        score: Composite score (0.0–1.0).
        trust_score: Trust component of the score.
        recency_score: Recency component of the score.
        relevance_score: Relevance component of the score.
    """

    item: ContextItem
    score: float
    trust_score: float
    recency_score: float
    relevance_score: float


class TrustAwareRetriever:
    """Retrieve context items scored by trust, recency, and keyword relevance.

    Scoring formula:
        ``score = w_trust * trust + w_recency * recency + w_relevance * relevance``

    Where:
    - **trust** = ``TRUST_ORDER[item.trust_level] / 3.0``
    - **recency** = ``exp(-age_seconds / half_life)``
    - **relevance** = keyword overlap ratio with query

    Args:
        weight_trust: Weight for trust component.
        weight_recency: Weight for recency component.
        weight_relevance: Weight for relevance component.
        recency_half_life: Seconds for recency score to halve.
    """

    def __init__(
        self,
        weight_trust: float = 0.3,
        weight_recency: float = 0.3,
        weight_relevance: float = 0.4,
        recency_half_life: float = 3600.0,
    ) -> None:
        self._w_trust = weight_trust
        self._w_recency = weight_recency
        self._w_relevance = weight_relevance
        self._half_life = recency_half_life

    def retrieve(
        self,
        ledger: ContextLedger,
        query: str,
        *,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> list[ScoredItem]:
        """Score and rank all items in the ledger against a query.

        Args:
            ledger: The context ledger to search.
            query: The query string for relevance scoring.
            top_k: Maximum results to return.
            min_score: Minimum composite score to include.

        Returns:
            Ranked list of ``ScoredItem`` objects.
        """
        now = time.time()
        query_words = set(query.lower().split())
        results: list[ScoredItem] = []

        for item in ledger.items:
            if item.is_expired:
                continue

            trust = TRUST_ORDER.get(item.trust_level, 0) / 3.0
            age = now - item.timestamp
            recency = math.exp(-age / self._half_life) if self._half_life > 0 else 0.0
            relevance = self._keyword_relevance(item.content, query_words)

            score = (
                self._w_trust * trust
                + self._w_recency * recency
                + self._w_relevance * relevance
            )

            if score >= min_score:
                results.append(
                    ScoredItem(
                        item=item,
                        score=score,
                        trust_score=trust,
                        recency_score=recency,
                        relevance_score=relevance,
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    @staticmethod
    def _keyword_relevance(content: str, query_words: set[str]) -> float:
        """Simple keyword overlap ratio."""
        if not query_words:
            return 0.0
        content_words = set(content.lower().split())
        overlap = query_words & content_words
        return len(overlap) / len(query_words) if query_words else 0.0
