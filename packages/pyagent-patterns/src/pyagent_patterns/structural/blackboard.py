"""Blackboard / Shared-State pattern: agents read/write a shared async store.

Agents don't communicate directly — they read from and write to a shared
blackboard. Each agent specializes in reading certain keys and writing others.

LLM calls: N agents x rounds
"""

from __future__ import annotations

from typing import Any

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class BlackboardEntry:
    """A typed entry on the blackboard with history."""

    def __init__(self, key: str, value: Any = None, author: str = "") -> None:
        self.key = key
        self.value = value
        self.author = author
        self.history: list[tuple[str, Any]] = []
        if value is not None:
            self.history.append((author, value))

    def update(self, value: Any, author: str) -> None:
        self.value = value
        self.author = author
        self.history.append((author, value))


class BlackboardState:
    """Shared state that agents read from and write to."""

    def __init__(self) -> None:
        self._entries: dict[str, BlackboardEntry] = {}

    def read(self, key: str) -> Any:
        entry = self._entries.get(key)
        return entry.value if entry else None

    def write(self, key: str, value: Any, author: str) -> None:
        if key in self._entries:
            self._entries[key].update(value, author)
        else:
            self._entries[key] = BlackboardEntry(key, value, author)

    def keys(self) -> list[str]:
        return list(self._entries.keys())

    def snapshot(self) -> dict[str, Any]:
        return {k: e.value for k, e in self._entries.items()}

    def __repr__(self) -> str:
        return f"BlackboardState({self.snapshot()})"


class BlackboardAgent:
    """An agent that reads from and writes to specific blackboard keys.

    Args:
        agent: The underlying LLM agent.
        reads: Keys this agent reads from the blackboard.
        writes: Keys this agent writes to the blackboard.
    """

    def __init__(self, agent: Agent, reads: list[str], writes: list[str]) -> None:
        self.agent = agent
        self.reads = reads
        self.writes = writes


class Blackboard(Pattern):
    """Shared-state communication via a blackboard store.

    Args:
        agents: List of BlackboardAgent wrappers specifying read/write keys.
        rounds: Number of rounds agents process the blackboard.
        initial_state: Optional initial blackboard values.
    """

    def __init__(
        self,
        agents: list[BlackboardAgent],
        rounds: int = 1,
        initial_state: dict[str, Any] | None = None,
    ) -> None:
        self._agents = agents
        self._rounds = rounds
        self._initial_state = initial_state or {}

    @property
    def pattern_type(self) -> str:
        return "blackboard"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        board = BlackboardState()

        # Initialize blackboard
        board.write("task", ctx.task, "system")
        for key, value in self._initial_state.items():
            board.write(key, value, "system")

        for _round_num in range(1, self._rounds + 1):
            for ba in self._agents:
                # Build prompt from readable keys
                readable = {k: board.read(k) for k in ba.reads if board.read(k) is not None}
                prompt = (
                    f"Task: {ctx.task}\n\n"
                    f"Blackboard state (your readable keys):\n"
                    + "\n".join(f"  {k}: {v}" for k, v in readable.items())
                    + f"\n\nYou must produce values for: {', '.join(ba.writes)}\n"
                    f"Respond with one value per line in format KEY: VALUE"
                )

                result = await ba.agent.run([Message.user(prompt)])
                messages.append(result)

                # Parse and write results to blackboard
                for line in result.content.split("\n"):
                    if ":" in line:
                        key, _, value = line.partition(":")
                        key = key.strip().lower().replace(" ", "_")
                        if key in ba.writes:
                            board.write(key, value.strip(), ba.agent.name)

        return Result(
            output=str(board.snapshot()),
            messages=messages,
            metadata={
                "rounds": self._rounds,
                "final_state": board.snapshot(),
                "agents": [a.agent.name for a in self._agents],
            },
        )
