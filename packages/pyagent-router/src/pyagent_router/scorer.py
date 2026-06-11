"""DifficultyScorer: estimate task difficulty to inform model routing.

Uses heuristics (token count, keyword complexity, question type) and
optionally an LLM classifier to score difficulty 1-10.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DifficultyScore:
    """Result of difficulty scoring.

    Attributes:
        score: Difficulty score from 1 (trivial) to 10 (extremely hard).
        signals: Dictionary of individual signal scores that contributed.
        category: Human-readable difficulty category.
    """

    score: int
    signals: dict[str, float] = field(default_factory=dict)
    category: str = ""

    @property
    def is_easy(self) -> bool:
        return self.score <= 3

    @property
    def is_medium(self) -> bool:
        return 4 <= self.score <= 6

    @property
    def is_hard(self) -> bool:
        return self.score >= 7


# Keywords indicating higher complexity
_COMPLEX_KEYWORDS = {
    "analyze",
    "compare",
    "contrast",
    "evaluate",
    "synthesize",
    "design",
    "architect",
    "optimize",
    "debug",
    "prove",
    "multi-step",
    "trade-off",
    "implications",
    "comprehensive",
    "algorithm",
    "mathematical",
    "formal",
    "derivation",
}

_SIMPLE_KEYWORDS = {
    "what is",
    "define",
    "list",
    "name",
    "when was",
    "who is",
    "how many",
    "yes or no",
    "true or false",
    "translate",
    "convert",
    "summarize",
}


class DifficultyScorer:
    """Heuristic-based task difficulty scorer.

    Scores tasks on a 1-10 scale using multiple signals:
    - Token length
    - Keyword complexity
    - Question structure
    - Required reasoning depth

    Args:
        custom_signals: Optional dict of custom signal functions.
            Each function takes a task string and returns a float 0-1.
    """

    def __init__(
        self,
        custom_signals: dict[str, Any] | None = None,
    ) -> None:
        self._custom_signals = custom_signals or {}

    def score(self, task: str) -> DifficultyScore:
        """Score the difficulty of a task string."""
        signals: dict[str, float] = {}

        # Signal 1: Length complexity (longer = harder, up to a point)
        word_count = len(task.split())
        signals["length"] = min(word_count / 200, 1.0)

        # Signal 2: Keyword complexity
        task_lower = task.lower()
        complex_hits = sum(1 for kw in _COMPLEX_KEYWORDS if kw in task_lower)
        simple_hits = sum(1 for kw in _SIMPLE_KEYWORDS if kw in task_lower)
        signals["keywords"] = min(complex_hits / 3, 1.0) - min(simple_hits / 3, 0.5)
        signals["keywords"] = max(0.0, signals["keywords"])

        # Signal 3: Multi-part questions (numbered steps, multiple questions)
        multi_part = len(re.findall(r"\d+\.", task)) + task.count("?") - 1
        signals["multi_part"] = min(max(multi_part, 0) / 5, 1.0)

        # Signal 4: Code/math indicators
        code_indicators = sum(
            1 for marker in ["```", "def ", "class ", "function", "import"] if marker in task
        )
        math_indicators = sum(
            1 for marker in ["∑", "∫", "equation", "formula", "proof"] if marker in task_lower
        )
        signals["technical"] = min((code_indicators + math_indicators) / 3, 1.0)

        # Custom signals
        for name, fn in self._custom_signals.items():
            signals[name] = float(fn(task))

        # Weighted average → 1-10 scale
        weights = {"length": 0.15, "keywords": 0.35, "multi_part": 0.25, "technical": 0.25}
        weighted_sum = sum(signals.get(k, 0) * w for k, w in weights.items())

        # Add custom signals with equal weight
        if self._custom_signals:
            custom_avg = sum(signals.get(k, 0) for k in self._custom_signals) / len(
                self._custom_signals
            )
            weighted_sum = weighted_sum * 0.7 + custom_avg * 0.3

        raw_score = max(1, min(10, int(weighted_sum * 10) + 1))

        category = "easy" if raw_score <= 3 else "medium" if raw_score <= 6 else "hard"

        return DifficultyScore(score=raw_score, signals=signals, category=category)
