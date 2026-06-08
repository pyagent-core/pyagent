"""Debate pattern: adversarial multi-round argumentation with a judge.

Multiple debater agents argue different positions over several rounds.
A judge agent evaluates arguments and renders a final decision.

LLM calls: D debaters × R rounds + 1 judge = D*R + 1
"""

from __future__ import annotations

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class Debate(Pattern):
    """Structured adversarial debate with judge resolution.

    Args:
        debaters: List of agents, each arguing a different position.
        judge: Agent that evaluates arguments and renders final decision.
        rounds: Number of argumentation rounds.
        positions: Optional list of position labels (e.g., ["BUY", "SELL"]).
            If not provided, positions are assigned as "Position 1", "Position 2", etc.
    """

    def __init__(
        self,
        debaters: list[Agent],
        judge: Agent,
        rounds: int = 3,
        positions: list[str] | None = None,
    ) -> None:
        if len(debaters) < 2:
            raise ValueError("Debate requires at least 2 debaters")
        self._debaters = debaters
        self._judge = judge
        self._rounds = rounds
        self._positions = positions or [f"Position {i + 1}" for i in range(len(debaters))]

    @property
    def pattern_type(self) -> str:
        return "debate"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        debate_log: list[dict[str, str]] = []
        round_args_prev: list[str] = []

        for round_num in range(1, self._rounds + 1):
            round_args: list[str] = []

            for i, debater in enumerate(self._debaters):
                position = self._positions[i]
                if round_num == 1:
                    prompt = Message.user(
                        f"You are arguing for '{position}' on this topic: {ctx.task}\n"
                        f"Present your opening argument."
                    )
                else:
                    opponent_args = "\n".join(
                        f"- {self._positions[j]}: {a}"
                        for j, a in enumerate(round_args_prev)
                        if j != i
                    )
                    prompt = Message.user(
                        f"You are arguing for '{position}'. Round {round_num}.\n"
                        f"Counter these arguments:\n{opponent_args}\n\n"
                        f"Strengthen your position."
                    )

                arg_result = await debater.run([prompt])
                messages.append(arg_result)
                round_args.append(arg_result.content)
                debate_log.append({
                    "round": round_num,
                    "debater": debater.name,
                    "position": position,
                    "argument": arg_result.content,
                })

            round_args_prev = round_args

        # Judge evaluates all arguments
        full_debate = "\n\n".join(
            f"[Round {entry['round']}] {entry['position']} ({entry['debater']}):\n{entry['argument']}"
            for entry in debate_log
        )
        judge_prompt = Message.user(
            f"You are the judge. Evaluate these arguments and render a final decision.\n"
            f"Topic: {ctx.task}\n\n{full_debate}\n\n"
            f"State your decision and reasoning."
        )
        verdict = await self._judge.run([judge_prompt])
        messages.append(verdict)

        return Result(
            output=verdict.content,
            messages=messages,
            metadata={
                "rounds": self._rounds,
                "debaters": [d.name for d in self._debaters],
                "positions": self._positions,
                "debate_log": debate_log,
            },
        )
