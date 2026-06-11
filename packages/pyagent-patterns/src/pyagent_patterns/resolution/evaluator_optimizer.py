"""Evaluator-Optimizer pattern: one agent generates, another evaluates against criteria.

The generator produces output, the evaluator scores it against predefined criteria.
If the score is below threshold, the generator revises based on evaluator feedback.

LLM calls: 2 per round (generate + evaluate) x rounds
"""

from __future__ import annotations

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class EvaluatorOptimizer(Pattern):
    """Generate → evaluate → revise loop with explicit evaluation criteria.

    Args:
        generator: Agent that produces and revises output.
        evaluator: Agent that scores output against criteria.
        criteria: List of evaluation criteria the evaluator checks.
        max_rounds: Maximum optimization rounds.
        pass_threshold: Score (1-10) at which the output is considered acceptable.
    """

    def __init__(
        self,
        generator: Agent,
        evaluator: Agent,
        criteria: list[str] | None = None,
        max_rounds: int = 3,
        pass_threshold: int = 7,
    ) -> None:
        self._generator = generator
        self._evaluator = evaluator
        self._criteria = criteria or ["correctness", "clarity", "completeness"]
        self._max_rounds = max_rounds
        self._pass_threshold = pass_threshold

    @property
    def pattern_type(self) -> str:
        return "evaluator_optimizer"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []
        current_output = ""
        scores: list[int] = []
        eval_text = ""

        criteria_text = "\n".join(f"- {c}" for c in self._criteria)

        for round_num in range(1, self._max_rounds + 1):
            # Generate or revise
            if round_num == 1:
                gen_prompt = Message.user(ctx.task)
            else:
                gen_prompt = Message.user(
                    f"Revise your output based on evaluator feedback:\n\n"
                    f"Previous output:\n{current_output}\n\n"
                    f"Feedback:\n{eval_text}"
                )
            gen_result = await self._generator.run([gen_prompt])
            messages.append(gen_result)
            current_output = gen_result.content

            # Evaluate
            eval_prompt = Message.user(
                f"Evaluate this output against these criteria:\n{criteria_text}\n\n"
                f"Output to evaluate:\n{current_output}\n\n"
                f"Provide a score (1-10) and specific feedback for improvement. "
                f"Format: SCORE: N\nFEEDBACK: ..."
            )
            eval_result = await self._evaluator.run([eval_prompt])
            messages.append(eval_result)

            eval_text = eval_result.content

            # Parse score
            score = self._parse_score(eval_text)
            scores.append(score)

            if score >= self._pass_threshold:
                break

        return Result(
            output=current_output,
            messages=messages,
            metadata={
                "rounds": round_num,
                "scores": scores,
                "final_score": scores[-1] if scores else 0,
                "passed": scores[-1] >= self._pass_threshold if scores else False,
                "criteria": self._criteria,
            },
        )

    @staticmethod
    def _parse_score(content: str) -> int:
        """Extract numeric score from evaluator response."""
        for line in content.split("\n"):
            line = line.strip().upper()
            if line.startswith("SCORE:"):
                try:
                    return int(line.split(":")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
        # Fallback: look for any number between 1-10
        import re

        numbers = re.findall(r"\b([1-9]|10)\b", content)
        return int(numbers[0]) if numbers else 5
