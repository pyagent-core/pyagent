"""Human-in-the-Loop pattern: approval gates at critical decision points.

An agent processes the task, then a human approval function decides
whether to accept, reject, or modify the output before it proceeds.

LLM calls: 1 agent + optional revision calls
"""

from __future__ import annotations

from collections.abc import Callable

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class HumanDecision:
    """Result of a human review."""

    def __init__(
        self,
        approved: bool,
        feedback: str = "",
        modified_output: str | None = None,
    ) -> None:
        self.approved = approved
        self.feedback = feedback
        self.modified_output = modified_output


# Type alias for the human review callback
HumanReviewFn = Callable[[str, dict[str, object]], HumanDecision]


def auto_approve(output: str, metadata: dict[str, object]) -> HumanDecision:
    """Default: auto-approve all outputs (for testing)."""
    return HumanDecision(approved=True)


class HumanInTheLoop(Pattern):
    """Agent with human approval gate.

    Args:
        agent: The LLM agent that processes the task.
        review_fn: Callable that presents output to human and returns decision.
            Signature: (output: str, metadata: dict) -> HumanDecision
        max_revisions: Maximum number of revision attempts after rejection.
    """

    def __init__(
        self,
        agent: Agent,
        review_fn: HumanReviewFn = auto_approve,
        max_revisions: int = 3,
    ) -> None:
        self._agent = agent
        self._review_fn = review_fn
        self._max_revisions = max_revisions

    @property
    def pattern_type(self) -> str:
        return "human_in_the_loop"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []

        # Initial agent response
        response = await self._agent.run(ctx.messages)
        messages.append(response)
        current_output = response.content

        for revision in range(self._max_revisions + 1):
            # Human review
            decision = self._review_fn(current_output, {"revision": revision, "task": ctx.task})

            if decision.approved:
                final_output = decision.modified_output or current_output
                return Result(
                    output=final_output,
                    messages=messages,
                    metadata={
                        "approved": True,
                        "revisions": revision,
                        "human_modified": decision.modified_output is not None,
                    },
                )

            if revision < self._max_revisions:
                # Revise based on human feedback
                revision_prompt = Message.user(
                    f"Revise your output based on this feedback:\n\n"
                    f"Your output:\n{current_output}\n\n"
                    f"Feedback:\n{decision.feedback}"
                )
                response = await self._agent.run([revision_prompt])
                messages.append(response)
                current_output = response.content

        # Max revisions exceeded — return last output with rejection flag
        return Result(
            output=current_output,
            messages=messages,
            metadata={"approved": False, "revisions": self._max_revisions},
        )
