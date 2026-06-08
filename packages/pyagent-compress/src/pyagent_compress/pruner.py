"""AgentPruner and InteractionPruner: reduce multi-agent overhead.

AgentPruner: detect and eliminate non-contributing agents mid-execution.
InteractionPruner: skip communication rounds when consensus is reached early.

Based on: arxiv:2503.18891 "AgentDropout: Dynamic Agent Elimination for Token-Efficient MAS"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyagent_patterns.base import Message


@dataclass(frozen=True)
class ContributionScore:
    """How much an agent is contributing to the conversation."""

    agent_name: str
    score: float  # 0-1
    unique_info: float  # 0-1 — how much unique information vs repetition
    message_count: int


class AgentPruner:
    """Detect and flag non-contributing agents for removal.

    Scores each agent's contribution based on:
    - Unique information (not repeated from other agents)
    - Response diversity (different from own previous responses)
    - Task relevance (overlap with original task keywords)

    Args:
        min_contribution: Minimum contribution score (0-1) to keep an agent.
        window_size: Number of recent messages to analyze per agent.
    """

    def __init__(self, min_contribution: float = 0.3, window_size: int = 5) -> None:
        self._min_contribution = min_contribution
        self._window_size = window_size

    def score_agents(
        self,
        messages: list[Message],
        task: str,
    ) -> list[ContributionScore]:
        """Score each agent's contribution from message history."""
        # Group messages by agent name
        by_agent: dict[str, list[str]] = {}
        for msg in messages:
            name = msg.name or "unknown"
            by_agent.setdefault(name, []).append(msg.content)

        [m.content for m in messages]
        task_words = set(task.lower().split())

        scores: list[ContributionScore] = []
        for agent_name, contents in by_agent.items():
            recent = contents[-self._window_size :]

            # Unique info: how much of this agent's content is NOT in other agents' content
            other_text = " ".join(
                c for name, cs in by_agent.items() if name != agent_name for c in cs
            ).lower()
            unique_words = set()
            for content in recent:
                for word in content.lower().split():
                    if word not in other_text and len(word) > 3:
                        unique_words.add(word)

            total_words = sum(len(c.split()) for c in recent)
            unique_ratio = len(unique_words) / max(total_words, 1)

            # Task relevance
            agent_words = set(" ".join(recent).lower().split())
            relevance = len(agent_words & task_words) / max(len(task_words), 1)

            # Self-diversity (are recent messages different from each other?)
            diversity = 1.0 - self._similarity(recent[-1], recent[-2]) if len(recent) >= 2 else 1.0

            score = 0.4 * unique_ratio + 0.3 * relevance + 0.3 * diversity
            scores.append(
                ContributionScore(
                    agent_name=agent_name,
                    score=min(score, 1.0),
                    unique_info=unique_ratio,
                    message_count=len(contents),
                )
            )

        return scores

    def should_prune(self, scores: list[ContributionScore]) -> list[str]:
        """Return agent names that should be pruned (below min contribution)."""
        return [s.agent_name for s in scores if s.score < self._min_contribution]

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Simple word-overlap similarity between two texts."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)


class InteractionPruner:
    """Detect early consensus and skip remaining communication rounds.

    Analyzes agent outputs to determine if consensus has been reached,
    allowing patterns like Debate or Voting to terminate early.

    Args:
        consensus_threshold: Minimum similarity between agent outputs
            to consider consensus reached (0-1).
        min_rounds: Minimum rounds before early termination is allowed.
    """

    def __init__(
        self,
        consensus_threshold: float = 0.7,
        min_rounds: int = 1,
    ) -> None:
        self._threshold = consensus_threshold
        self._min_rounds = min_rounds

    def has_consensus(self, outputs: list[str], current_round: int) -> bool:
        """Check if agents have reached consensus.

        Args:
            outputs: Current round's outputs from all agents.
            current_round: The current round number (1-indexed).

        Returns:
            True if consensus is reached and we can stop early.
        """
        if current_round < self._min_rounds:
            return False

        if len(outputs) < 2:
            return True

        # Check pairwise similarity
        similarities: list[float] = []
        for i in range(len(outputs)):
            for j in range(i + 1, len(outputs)):
                sim = self._similarity(outputs[i], outputs[j])
                similarities.append(sim)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        return avg_similarity >= self._threshold

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)
