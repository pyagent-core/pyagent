"""MessageCompressor: reduce inter-agent message size while preserving key information.

Implements extractive compression: keeps the most important sentences
from verbose LLM reasoning traces, stripping filler and repetition.

Based on: "Cut the Crap: Economical Communication Pipeline for LLM-based MAS" (2024)
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CompressionResult:
    """Result of message compression.

    Attributes:
        original: The original text.
        compressed: The compressed text.
        original_tokens: Estimated original token count.
        compressed_tokens: Estimated compressed token count.
        savings_pct: Percentage of tokens saved (0-1).
    """

    original: str
    compressed: str
    original_tokens: int
    compressed_tokens: int

    @property
    def savings_pct(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return 1.0 - (self.compressed_tokens / self.original_tokens)


# Filler phrases commonly found in LLM reasoning traces
_FILLER_PATTERNS = [
    r"(?i)\b(let me think|let's think|okay so|well|basically|essentially|in other words)\b[,.]?\s*",
    r"(?i)\b(as I mentioned|as we discussed|to summarize so far|in summary)\b[,.]?\s*",
    r"(?i)\b(it's worth noting that|it's important to note that|I should mention that)\b\s*",
    r"(?i)\b(first of all|secondly|thirdly|finally|in conclusion)\b[,.]?\s*",
    r"(?i)\b(I think|I believe|in my opinion|from my perspective)\b[,.]?\s*",
]


class MessageCompressor:
    """Compress inter-agent messages by removing filler and extracting key sentences.

    Args:
        target_ratio: Target compression ratio (0.3 = keep 30% of tokens).
        min_sentence_length: Minimum characters for a sentence to be kept.
        remove_filler: Whether to strip filler phrases.
    """

    def __init__(
        self,
        target_ratio: float = 0.5,
        min_sentence_length: int = 20,
        remove_filler: bool = True,
    ) -> None:
        self._target_ratio = target_ratio
        self._min_sentence_length = min_sentence_length
        self._remove_filler = remove_filler

    def compress(self, text: str) -> CompressionResult:
        """Compress a message text.

        Strategy:
        1. Remove filler phrases
        2. Split into sentences
        3. Score sentences by information density
        4. Keep top sentences until target ratio met
        """
        original_tokens = len(text) // 4

        if original_tokens <= 20:
            # Too short to compress meaningfully
            return CompressionResult(text, text, original_tokens, original_tokens)

        working = text

        # Step 1: Remove filler
        if self._remove_filler:
            for pattern in _FILLER_PATTERNS:
                working = re.sub(pattern, "", working)

        # Step 2: Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", working)
        sentences = [s.strip() for s in sentences if len(s.strip()) >= self._min_sentence_length]

        if not sentences:
            compressed_tokens = len(working) // 4
            return CompressionResult(text, working.strip(), original_tokens, compressed_tokens)

        # Step 3: Score sentences
        scored = [(self._score_sentence(s), s) for s in sentences]
        scored.sort(key=lambda x: x[0], reverse=True)

        # Step 4: Keep top sentences until target ratio
        target_tokens = int(original_tokens * self._target_ratio)
        kept: list[str] = []
        running_tokens = 0

        for _score, sentence in scored:
            sent_tokens = len(sentence) // 4
            if running_tokens + sent_tokens > target_tokens and kept:
                break
            kept.append(sentence)
            running_tokens += sent_tokens

        # Restore original order
        ordered = [s for s in sentences if s in kept]
        compressed = " ".join(ordered)
        compressed_tokens = len(compressed) // 4

        return CompressionResult(text, compressed, original_tokens, compressed_tokens)

    @staticmethod
    def _score_sentence(sentence: str) -> float:
        """Score a sentence by information density (higher = more informative)."""
        score = 0.0

        # Longer sentences tend to carry more information (diminishing returns)
        score += min(len(sentence.split()) / 20, 1.0) * 0.3

        # Sentences with numbers/data are more informative
        numbers = len(re.findall(r"\d+\.?\d*", sentence))
        score += min(numbers / 3, 1.0) * 0.3

        # Sentences with technical terms
        technical = len(re.findall(
            r"(?i)\b(result|conclusion|therefore|because|shows|indicates|found|"
            r"evidence|data|percent|increase|decrease|significant)\b", sentence
        ))
        score += min(technical / 3, 1.0) * 0.2

        # Shorter sentences with substance are preferred
        if 10 <= len(sentence.split()) <= 25:
            score += 0.2

        return score
