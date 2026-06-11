"""Tests for ContextCompressor: FIFO, semantic_lossless, sawtooth, threshold."""

from __future__ import annotations

import time

from pyagent_context.compression import CompressionPolicy, ContextCompressor
from pyagent_context.item import ContextItem, TrustLevel
from pyagent_context.ledger import ContextLedger


def _make_ledger(n: int, tokens_per_item: int = 100) -> ContextLedger:
    """Create a ledger with n items, each having tokens_per_item tokens."""
    ledger = ContextLedger()
    for i in range(n):
        content = f"Item {i}: " + "x" * (tokens_per_item * 4)
        ledger.append(
            ContextItem(
                content=content,
                source="test",
                timestamp=time.time() - (n - i),
                token_estimate=tokens_per_item,
            )
        )
    return ledger


def test_none_policy() -> None:
    compressor = ContextCompressor(policy=CompressionPolicy.NONE)
    ledger = _make_ledger(10, 200)
    assert not compressor.should_compress(ledger)
    result = compressor.compress(ledger)
    assert len(result) == 10


def test_fifo_should_compress() -> None:
    compressor = ContextCompressor(
        policy=CompressionPolicy.FIFO,
        threshold_tokens=500,
        floor_tokens=200,
    )
    ledger = _make_ledger(10, 100)  # 1000 tokens total
    assert compressor.should_compress(ledger)


def test_fifo_compress() -> None:
    compressor = ContextCompressor(
        policy=CompressionPolicy.FIFO,
        threshold_tokens=500,
        floor_tokens=200,
    )
    ledger = _make_ledger(10, 100)  # 1000 tokens
    result = compressor.compress(ledger)
    assert result.total_tokens <= 200


def test_fifo_preserves_verified() -> None:
    ledger = ContextLedger()
    ledger.append(
        ContextItem(
            content="Verified fact",
            source="test",
            trust_level=TrustLevel.VERIFIED,
            token_estimate=100,
        )
    )
    for i in range(9):
        ledger.append(
            ContextItem(
                content=f"Inferred {i}",
                source="test",
                token_estimate=100,
            )
        )

    compressor = ContextCompressor(
        policy=CompressionPolicy.FIFO,
        threshold_tokens=500,
        floor_tokens=200,
    )
    result = compressor.compress(ledger)
    verified = [i for i in result.items if i.trust_level == TrustLevel.VERIFIED]
    assert len(verified) == 1


def test_semantic_lossless() -> None:
    ledger = ContextLedger()
    ledger.append(
        ContextItem(
            content="First sentence. Second sentence. Third sentence.",
            source="test",
            token_estimate=50,
        )
    )
    ledger.append(
        ContextItem(
            content="Verified content stays intact",
            source="test",
            trust_level=TrustLevel.VERIFIED,
            token_estimate=50,
        )
    )

    compressor = ContextCompressor(
        policy=CompressionPolicy.SEMANTIC_LOSSLESS,
        threshold_tokens=50,
        floor_tokens=30,
    )
    result = compressor.compress(ledger)
    # Inferred item compressed to first sentence
    inferred = [i for i in result.items if i.trust_level != TrustLevel.VERIFIED]
    assert len(inferred) == 1
    assert "Second" not in inferred[0].content
    # Verified item unchanged
    verified = [i for i in result.items if i.trust_level == TrustLevel.VERIFIED]
    assert verified[0].content == "Verified content stays intact"


def test_sawtooth() -> None:
    compressor = ContextCompressor(
        policy=CompressionPolicy.SAWTOOTH,
        threshold_tokens=500,
        floor_tokens=200,
    )
    ledger = _make_ledger(10, 100)  # 1000 tokens
    assert compressor.should_compress(ledger)
    result = compressor.compress(ledger)
    assert result.total_tokens < ledger.total_tokens
