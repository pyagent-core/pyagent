"""Role-Based Cooperation pattern: agents adopt distinct functional roles.

Most frequently used pattern (46.8% in arxiv:2511.08475).
Each agent has a specialized role and they communicate in a structured order.

LLM calls: N agents × rounds
"""

from __future__ import annotations

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class RoleBased(Pattern):
    """Agents with distinct roles collaborate in structured rounds.

    Args:
        agents: List of role-specialized agents (order matters for turn-taking).
        rounds: Number of communication rounds.
        shared_context: If True, all agents see all prior messages. If False,
            each agent only sees the immediately preceding message.
    """

    def __init__(
        self,
        agents: list[Agent],
        rounds: int = 1,
        shared_context: bool = True,
    ) -> None:
        self._agents = agents
        self._rounds = rounds
        self._shared_context = shared_context

    @property
    def pattern_type(self) -> str:
        return "role_based"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        conversation: list[Message] = [Message.user(ctx.task)]

        for round_num in range(1, self._rounds + 1):
            for agent in self._agents:
                if self._shared_context:
                    input_msgs = list(conversation)
                else:
                    input_msgs = [conversation[-1]] if conversation else [Message.user(ctx.task)]

                response = await agent.run(input_msgs)
                messages.append(response)
                conversation.append(response)

        return Result(
            output=conversation[-1].content,
            messages=messages,
            metadata={
                "rounds": self._rounds,
                "roles": [a.name for a in self._agents],
                "shared_context": self._shared_context,
            },
        )
