"""Self-Reflection pattern: generate → self-critique → refine loop.

The agent generates an initial output, critiques it for errors,
then produces a revised output. Repeats until max rounds or confidence met.

LLM calls: 2 per round × 1-N rounds = 2-2N
"""

from __future__ import annotations

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class SelfReflection(Pattern):
    """Generate → critique → refine iterative loop.

    Args:
        agent: The agent that generates and refines output.
        critic: Optional separate critic agent. If None, the same agent self-critiques.
        max_rounds: Maximum number of generate-critique rounds.
        stop_phrase: If the critic's response contains this phrase, stop early.
    """

    def __init__(
        self,
        agent: Agent,
        critic: Agent | None = None,
        max_rounds: int = 3,
        stop_phrase: str = "APPROVED",
    ) -> None:
        self._agent = agent
        self._critic = critic or agent
        self._max_rounds = max_rounds
        self._stop_phrase = stop_phrase

    @property
    def pattern_type(self) -> str:
        return "self_reflection"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        current_output = ""

        for round_num in range(1, self._max_rounds + 1):
            # Generate (or refine)
            if round_num == 1:
                gen_prompt = Message.user(ctx.task)
            else:
                gen_prompt = Message.user(
                    f"Revise your previous output based on this feedback:\n\n"
                    f"Previous output:\n{current_output}\n\n"
                    f"Feedback:\n{critique_text}"
                )
            gen_result = await self._agent.run([gen_prompt])
            messages.append(gen_result)
            current_output = gen_result.content

            # Critique
            critique_prompt = Message.user(
                f"Review the following output for errors, gaps, or improvements. "
                f"If the output is satisfactory, respond with '{self._stop_phrase}'. "
                f"Otherwise, provide specific feedback.\n\n"
                f"Output to review:\n{current_output}"
            )
            critique_result = await self._critic.run([critique_prompt])
            messages.append(critique_result)
            critique_text = critique_result.content

            if self._stop_phrase in critique_result.content:
                break

        return Result(
            output=current_output,
            messages=messages,
            metadata={
                "rounds": round_num,
                "max_rounds": self._max_rounds,
                "early_stop": self._stop_phrase in messages[-1].content,
            },
        )
