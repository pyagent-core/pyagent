"""CostTracker: accumulate and attribute costs by pattern, agent, and model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostEntry:
    """A single cost record."""

    pattern_type: str
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostTracker:
    """Track costs across an entire workflow.

    Usage:
        tracker = CostTracker()
        tracker.record("debate", "bull_agent", "gpt-4o", 500, 200, 0.003)
        tracker.record("debate", "bear_agent", "gpt-4o-mini", 500, 200, 0.0004)
        print(tracker.summary())
    """

    def __init__(self) -> None:
        self._entries: list[CostEntry] = []

    def record(
        self,
        pattern_type: str,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """Record a cost entry."""
        self._entries.append(
            CostEntry(
                pattern_type=pattern_type,
                agent_name=agent_name,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
            )
        )

    @property
    def total_cost(self) -> float:
        return sum(e.cost_usd for e in self._entries)

    @property
    def total_tokens(self) -> int:
        return sum(e.input_tokens + e.output_tokens for e in self._entries)

    def by_pattern(self) -> dict[str, float]:
        """Cost breakdown by pattern type."""
        result: dict[str, float] = {}
        for e in self._entries:
            result[e.pattern_type] = result.get(e.pattern_type, 0.0) + e.cost_usd
        return result

    def by_agent(self) -> dict[str, float]:
        """Cost breakdown by agent name."""
        result: dict[str, float] = {}
        for e in self._entries:
            result[e.agent_name] = result.get(e.agent_name, 0.0) + e.cost_usd
        return result

    def by_model(self) -> dict[str, float]:
        """Cost breakdown by model."""
        result: dict[str, float] = {}
        for e in self._entries:
            result[e.model] = result.get(e.model, 0.0) + e.cost_usd
        return result

    def summary(self) -> dict[str, object]:
        """Full cost summary."""
        return {
            "total_cost_usd": self.total_cost,
            "total_tokens": self.total_tokens,
            "entries": len(self._entries),
            "by_pattern": self.by_pattern(),
            "by_agent": self.by_agent(),
            "by_model": self.by_model(),
        }
