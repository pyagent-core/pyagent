"""ContextCompressor: compression policies for context ledger management."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pyagent_context.item import ContextItem, TrustLevel
from pyagent_context.ledger import ContextLedger

if TYPE_CHECKING:
    pass


class CompressionPolicy(StrEnum):
    """Available compression strategies."""

    NONE = "none"
    FIFO = "fifo"                               # drop oldest items
    SEMANTIC_LOSSLESS = "semantic_lossless"      # compress text, keep Knowledge block
    SAWTOOTH = "sawtooth"                        # compress to floor, grow again


class ContextCompressor:
    """Apply compression policies to a ContextLedger.

    The compressor monitors token usage and compresses when a threshold
    is reached.

    Args:
        policy: Compression strategy.
        threshold_tokens: Token count that triggers compression.
        floor_tokens: Token target after compression (for SAWTOOTH/FIFO).
        preserve_trust: Items at or above this trust level are never dropped.
    """

    def __init__(
        self,
        policy: CompressionPolicy = CompressionPolicy.FIFO,
        threshold_tokens: int = 10_000,
        floor_tokens: int = 5_000,
        preserve_trust: TrustLevel = TrustLevel.VERIFIED,
    ) -> None:
        self._policy = policy
        self._threshold = threshold_tokens
        self._floor = floor_tokens
        self._preserve_trust = preserve_trust

    @property
    def policy(self) -> CompressionPolicy:
        return self._policy

    def should_compress(self, ledger: ContextLedger) -> bool:
        """Check if the ledger's token count exceeds the threshold."""
        if self._policy == CompressionPolicy.NONE:
            return False
        return ledger.total_tokens >= self._threshold

    def compress(self, ledger: ContextLedger) -> ContextLedger:
        """Apply the compression policy and return a new (compressed) ledger.

        The original ledger is not mutated.
        """
        if self._policy == CompressionPolicy.NONE:
            return ledger
        if self._policy == CompressionPolicy.FIFO:
            return self._compress_fifo(ledger)
        if self._policy == CompressionPolicy.SEMANTIC_LOSSLESS:
            return self._compress_semantic(ledger)
        if self._policy == CompressionPolicy.SAWTOOTH:
            return self._compress_sawtooth(ledger)
        return ledger

    def _compress_fifo(self, ledger: ContextLedger) -> ContextLedger:
        """Drop oldest items until under floor, preserving high-trust items."""
        items = list(ledger.items)
        tokens = ledger.total_tokens

        # Remove from front (oldest) until under floor
        new_items: list[ContextItem] = []
        for item in items:
            if tokens <= self._floor:
                new_items.append(item)
            elif item.trust_level >= self._preserve_trust:
                new_items.append(item)  # keep high-trust
            else:
                tokens -= item.token_estimate  # drop

        return ContextLedger(items=new_items)

    def _compress_semantic(self, ledger: ContextLedger) -> ContextLedger:
        """Compress item content text while preserving verified items unchanged.

        Uses simple sentence extraction — for full compression, integrate
        ``MessageCompressor`` from ``pyagent-compress``.
        """
        items = list(ledger.items)
        new_items: list[ContextItem] = []

        for item in items:
            if item.trust_level >= self._preserve_trust:
                new_items.append(item)
            else:
                # Simple compression: keep first sentence only
                sentences = item.content.split(". ")
                compressed = sentences[0] + ("." if len(sentences) > 1 else "")
                new_item = ContextItem(
                    content=compressed,
                    source=item.source,
                    timestamp=item.timestamp,
                    trust_level=item.trust_level,
                    sensitivity=item.sensitivity,
                    expires_at=item.expires_at,
                    derived_from=item.id,
                )
                new_items.append(new_item)

        return ContextLedger(items=new_items)

    def _compress_sawtooth(self, ledger: ContextLedger) -> ContextLedger:
        """Compress to floor, then allow growth again.

        Combines FIFO eviction with semantic compression for remaining items.
        """
        # First pass: FIFO eviction
        fifo_result = self._compress_fifo(ledger)

        # If still over floor, apply semantic compression
        if fifo_result.total_tokens > self._floor:
            return self._compress_semantic(fifo_result)

        return fifo_result
