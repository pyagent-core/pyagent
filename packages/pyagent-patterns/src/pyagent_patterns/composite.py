"""Composite patterns: chain/nest multiple patterns with escalation triggers.

CompositePattern runs patterns in sequence, escalating to the next
if the current pattern's result doesn't meet a quality check.

EscalationChain is a pre-built composite: Reflection → Debate → Voting → Human.
"""

from __future__ import annotations

from collections.abc import Callable

from pyagent_patterns.base import Context, Pattern, Result

# Quality check: returns True if the result is acceptable
QualityCheckFn = Callable[[Result], bool]


def always_pass(result: Result) -> bool:
    """Default quality check: always passes."""
    return True


def min_length_check(min_chars: int = 50) -> QualityCheckFn:
    """Quality check: output must be at least min_chars characters."""

    def check(result: Result) -> bool:
        return len(result.output) >= min_chars

    return check


class CompositePattern(Pattern):
    """Chain multiple patterns with escalation on quality failure.

    Args:
        patterns: Ordered list of patterns to try.
        quality_check: Function that evaluates whether a pattern's result
            is acceptable. If it returns False, the next pattern is tried.
        combine_results: If True, passes previous output as context to next pattern.
    """

    def __init__(
        self,
        patterns: list[Pattern],
        quality_check: QualityCheckFn = always_pass,
        combine_results: bool = True,
    ) -> None:
        if not patterns:
            raise ValueError("CompositePattern requires at least one pattern")
        self._patterns = patterns
        self._quality_check = quality_check
        self._combine_results = combine_results

    @property
    def pattern_type(self) -> str:
        types = [p.pattern_type for p in self._patterns]
        return f"composite({'+'.join(types)})"

    async def _execute(self, ctx: Context) -> Result:
        all_messages = []
        escalation_log = []

        for i, pattern in enumerate(self._patterns):
            # Create child context for each pattern
            child_ctx = ctx.child()

            result = await pattern._execute(child_ctx)
            all_messages.extend(result.messages)
            escalation_log.append(
                {
                    "pattern": pattern.pattern_type,
                    "output_length": len(result.output),
                    "metadata": result.metadata,
                }
            )

            if self._quality_check(result):
                return Result(
                    output=result.output,
                    messages=all_messages,
                    metadata={
                        "escalation_level": i,
                        "pattern_used": pattern.pattern_type,
                        "escalation_log": escalation_log,
                        "total_patterns_tried": i + 1,
                    },
                )

            # If not last pattern and combining, update context with current output
            if self._combine_results and i < len(self._patterns) - 1:
                ctx.metadata["previous_output"] = result.output
                ctx.metadata["previous_pattern"] = pattern.pattern_type

        # All patterns tried, return last result
        return Result(
            output=result.output,
            messages=all_messages,
            metadata={
                "escalation_level": len(self._patterns) - 1,
                "pattern_used": self._patterns[-1].pattern_type,
                "escalation_log": escalation_log,
                "total_patterns_tried": len(self._patterns),
                "fully_escalated": True,
            },
        )
