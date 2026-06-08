"""Voting pattern: multiple agents vote independently, majority wins.

Each agent produces an answer independently (can run in parallel).
Supports majority voting, weighted voting, and ranked-choice.

LLM calls: N agents (parallel)
"""

from __future__ import annotations

import asyncio
from collections import Counter
from enum import StrEnum

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class VotingStrategy(StrEnum):
    MAJORITY = "majority"
    WEIGHTED = "weighted"


class Voting(Pattern):
    """Independent voting with configurable aggregation strategy.

    Args:
        voters: List of agents that each cast a vote.
        strategy: Voting strategy (majority or weighted).
        weights: Optional per-agent weights for weighted voting.
            Must match length of voters. Defaults to equal weights.
        normalize: If True, ask each voter to respond with a concise answer
            suitable for comparison.
    """

    def __init__(
        self,
        voters: list[Agent],
        strategy: VotingStrategy = VotingStrategy.MAJORITY,
        weights: list[float] | None = None,
        normalize: bool = True,
    ) -> None:
        if len(voters) < 2:
            raise ValueError("Voting requires at least 2 voters")
        self._voters = voters
        self._strategy = strategy
        self._weights = weights or [1.0] * len(voters)
        self._normalize = normalize

    @property
    def pattern_type(self) -> str:
        return "voting"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []

        suffix = ""
        if self._normalize:
            suffix = "\n\nRespond with a concise answer (one word or short phrase) first, then explain."

        # All voters run in parallel
        tasks = [
            voter.run([Message.user(ctx.task + suffix)]) for voter in self._voters
        ]
        votes = await asyncio.gather(*tasks)
        messages.extend(votes)

        # Extract vote labels (first line of each response)
        vote_labels = [v.content.strip().split("\n")[0].strip() for v in votes]

        # Tally
        if self._strategy == VotingStrategy.MAJORITY:
            counter = Counter(vote_labels)
            winner = counter.most_common(1)[0][0]
            tally = dict(counter)
        else:
            # Weighted voting
            weighted_counts: dict[str, float] = {}
            for label, weight in zip(vote_labels, self._weights, strict=False):
                weighted_counts[label] = weighted_counts.get(label, 0.0) + weight
            winner = max(weighted_counts, key=weighted_counts.get)  # type: ignore[arg-type]
            tally = weighted_counts

        return Result(
            output=winner,
            messages=messages,
            metadata={
                "strategy": self._strategy.value,
                "votes": vote_labels,
                "tally": tally,
                "winner": winner,
                "voter_names": [v.name for v in self._voters],
            },
        )
