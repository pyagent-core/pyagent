"""TokenBudget: enforce per-agent and per-workflow token limits.

Tracks token consumption across a workflow and raises BudgetExceededError
when limits are hit, enabling graceful degradation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceededError(Exception):
    """Raised when a token budget is exceeded."""

    def __init__(self, agent: str, used: int, limit: int) -> None:
        self.agent = agent
        self.used = used
        self.limit = limit
        super().__init__(f"Agent '{agent}' exceeded budget: {used}/{limit} tokens")


@dataclass
class AgentBudget:
    """Budget tracking for a single agent."""

    name: str
    limit: int
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def utilization(self) -> float:
        return self.used / self.limit if self.limit > 0 else 0.0

    def consume(self, tokens: int, strict: bool = True) -> None:
        """Consume tokens from budget.

        Args:
            tokens: Number of tokens consumed.
            strict: If True, raises BudgetExceededError. If False, just tracks.
        """
        self.used += tokens
        if strict and self.used > self.limit:
            raise BudgetExceededError(self.name, self.used, self.limit)


@dataclass
class TokenBudget:
    """Manage token budgets across a multi-agent workflow.

    Args:
        workflow_limit: Total token limit across all agents.
        per_agent_limit: Default per-agent token limit.
        strict: If True, raises BudgetExceededError on limit violations.
    """

    workflow_limit: int = 100_000
    per_agent_limit: int = 20_000
    strict: bool = True
    _agents: dict[str, AgentBudget] = field(default_factory=dict)
    _total_used: int = 0

    def register_agent(self, name: str, limit: int | None = None) -> None:
        """Register an agent with an optional custom limit."""
        self._agents[name] = AgentBudget(name=name, limit=limit or self.per_agent_limit)

    def consume(self, agent_name: str, tokens: int) -> None:
        """Record token consumption for an agent.

        Args:
            agent_name: The consuming agent's name.
            tokens: Number of tokens consumed.
        """
        if agent_name not in self._agents:
            self.register_agent(agent_name)

        self._agents[agent_name].consume(tokens, strict=self.strict)
        self._total_used += tokens

        if self.strict and self._total_used > self.workflow_limit:
            raise BudgetExceededError("workflow", self._total_used, self.workflow_limit)

    def remaining(self, agent_name: str | None = None) -> int:
        """Get remaining tokens for an agent or the whole workflow."""
        if agent_name:
            budget = self._agents.get(agent_name)
            return budget.remaining if budget else self.per_agent_limit
        return max(0, self.workflow_limit - self._total_used)

    @property
    def total_used(self) -> int:
        return self._total_used

    @property
    def workflow_utilization(self) -> float:
        return self._total_used / self.workflow_limit if self.workflow_limit > 0 else 0.0

    def summary(self) -> dict[str, dict[str, int | float]]:
        """Return a summary of all agent budgets."""
        result: dict[str, dict[str, int | float]] = {
            "workflow": {
                "limit": self.workflow_limit,
                "used": self._total_used,
                "remaining": self.remaining(),
                "utilization": self.workflow_utilization,
            }
        }
        for name, budget in self._agents.items():
            result[name] = {
                "limit": budget.limit,
                "used": budget.used,
                "remaining": budget.remaining,
                "utilization": budget.utilization,
            }
        return result
