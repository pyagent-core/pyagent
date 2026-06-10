"""Tests for TrustAwareRetriever: scoring and filtered retrieval."""

from __future__ import annotations

import time

from pyagent_context.item import ContextItem, TrustLevel
from pyagent_context.ledger import ContextLedger
from pyagent_context.retrieval import TrustAwareRetriever


def test_retrieval_ranks_by_relevance() -> None:
    ledger = ContextLedger()
    ledger.append(ContextItem(content="Python asyncio concurrency patterns", source="s"))
    ledger.append(ContextItem(content="JavaScript React component", source="s"))
    ledger.append(ContextItem(content="Python FastAPI async web framework", source="s"))

    retriever = TrustAwareRetriever(weight_relevance=0.8, weight_trust=0.1, weight_recency=0.1)
    results = retriever.retrieve(ledger, "Python async web")

    assert len(results) >= 2
    # Items with Python/async keywords should score highest
    top_content = results[0].item.content.lower()
    assert "python" in top_content


def test_retrieval_ranks_by_trust() -> None:
    now = time.time()
    ledger = ContextLedger()
    ledger.append(ContextItem(
        content="Database connection pooling",
        source="s",
        trust_level=TrustLevel.INFERRED,
        timestamp=now,
    ))
    ledger.append(ContextItem(
        content="Database connection pooling",
        source="s",
        trust_level=TrustLevel.VERIFIED,
        timestamp=now,
    ))

    retriever = TrustAwareRetriever(weight_trust=0.9, weight_relevance=0.05, weight_recency=0.05)
    results = retriever.retrieve(ledger, "database connection")

    assert len(results) == 2
    assert results[0].item.trust_level == TrustLevel.VERIFIED
    assert results[0].trust_score > results[1].trust_score


def test_retrieval_excludes_expired() -> None:
    ledger = ContextLedger()
    ledger.append(ContextItem(
        content="expired item about Python",
        source="s",
        expires_at=time.time() - 10,
    ))
    ledger.append(ContextItem(content="active item about Python", source="s"))

    retriever = TrustAwareRetriever()
    results = retriever.retrieve(ledger, "Python")

    assert len(results) == 1
    assert results[0].item.content == "active item about Python"


def test_retrieval_min_score_filter() -> None:
    ledger = ContextLedger()
    ledger.append(ContextItem(content="completely irrelevant nonsense xyz", source="s"))
    ledger.append(ContextItem(content="Python async patterns", source="s"))

    retriever = TrustAwareRetriever()
    results = retriever.retrieve(ledger, "Python async", min_score=0.1)

    # Only the relevant item should pass the min_score filter
    for r in results:
        assert r.score >= 0.1


def test_retrieval_top_k() -> None:
    ledger = ContextLedger()
    for i in range(20):
        ledger.append(ContextItem(content=f"Item {i} about Python", source="s"))

    retriever = TrustAwareRetriever()
    results = retriever.retrieve(ledger, "Python", top_k=5)
    assert len(results) <= 5
