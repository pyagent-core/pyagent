"""Cross-Reflection pattern: Agent A generates → Agent B reviews → Agent A revises.

Unlike Self-Reflection where one agent critiques itself, Cross-Reflection
uses a separate peer agent to provide independent feedback, reducing bias.

LLM calls: 3 minimum (generate + review + revise)
"""

from __future__ import annotations

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class CrossReflection(Pattern):
    """Peer review: one agent generates, another reviews, generator revises.

    Args:
        generator: Agent that produces the initial output and revisions.
        reviewer: Agent that reviews and provides feedback.
        max_rounds: Maximum number of generate-review-revise cycles.
        stop_phrase: If reviewer says this, stop early.
    """

    def __init__(
        self,
        generator: Agent,
        reviewer: Agent,
        max_rounds: int = 2,
        stop_phrase: str = "APPROVED",
    ) -> None:
        self._generator = generator
        self._reviewer = reviewer
        self._max_rounds = max_rounds
        self._stop_phrase = stop_phrase

    @property
    def pattern_type(self) -> str:
        return "cross_reflection"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        current_output = ""
        review_text = ""

        for round_num in range(1, self._max_rounds + 1):
            # Generate or revise
            if round_num == 1:
                gen_prompt = Message.user(ctx.task)
            else:
                gen_prompt = Message.user(
                    f"Revise based on peer feedback:\n\n"
                    f"Your output:\n{current_output}\n\n"
                    f"Peer feedback:\n{review_text}"
                )
            gen_result = await self._generator.run([gen_prompt])
            messages.append(gen_result)
            current_output = gen_result.content

            # Peer review
            review_prompt = Message.user(
                f"Review this output from your peer. Provide constructive feedback. "
                f"If the output is satisfactory, respond with '{self._stop_phrase}'.\n\n"
                f"{current_output}"
            )
            review_result = await self._reviewer.run([review_prompt])
            messages.append(review_result)

            review_text = review_result.content

            if self._stop_phrase in review_text:
                break

        return Result(
            output=current_output,
            messages=messages,
            metadata={
                "rounds": round_num,
                "generator": self._generator.name,
                "reviewer": self._reviewer.name,
            },
        )
