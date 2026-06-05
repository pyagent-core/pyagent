"""Talker-Reasoner pattern: System 1 (fast/cheap) + System 2 (slow/expensive).

Inspired by Kahneman's dual-process theory and Google DeepMind's 2024 paper.
A fast "talker" handles routine queries; a slow "reasoner" is activated
only for complex queries that exceed a complexity threshold.

LLM calls: 1 (easy) or 2 (hard: classifier + reasoner) or 3 (with classifier)
"""

from __future__ import annotations

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class TalkerReasoner(Pattern):
    """Dual-process: fast intuition (System 1) + slow deliberation (System 2).

    Args:
        talker: Fast, cheap agent for routine queries (System 1).
        reasoner: Slow, expensive agent for complex queries (System 2).
        classifier: Optional agent that decides talker vs reasoner.
            If None, always starts with talker and escalates on uncertainty keywords.
        complexity_threshold: Keywords in talker output that trigger escalation to reasoner.
    """

    def __init__(
        self,
        talker: Agent,
        reasoner: Agent,
        classifier: Agent | None = None,
        complexity_threshold: list[str] | None = None,
    ) -> None:
        self._talker = talker
        self._reasoner = reasoner
        self._classifier = classifier
        self._complexity_keywords = complexity_threshold or [
            "I'm not sure",
            "I don't know",
            "complex",
            "need to think",
            "uncertain",
            "ESCALATE",
        ]

    @property
    def pattern_type(self) -> str:
        return "talker_reasoner"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []

        if self._classifier:
            # Use classifier to decide
            classify_prompt = Message.user(
                f"Is this query simple or complex? "
                f"Respond with exactly 'SIMPLE' or 'COMPLEX'.\n\n"
                f"Query: {ctx.task}"
            )
            classification = await self._classifier.run([classify_prompt])
            messages.append(classification)
            use_reasoner = "COMPLEX" in classification.content.upper()
        else:
            use_reasoner = False

        if not use_reasoner:
            # System 1: fast talker
            talker_result = await self._talker.run(ctx.messages)
            messages.append(talker_result)

            # Check if talker signals uncertainty → escalate to reasoner
            should_escalate = any(
                kw.lower() in talker_result.content.lower() for kw in self._complexity_keywords
            )

            if should_escalate:
                use_reasoner = True
            else:
                return Result(
                    output=talker_result.content,
                    messages=messages,
                    metadata={"system": "talker", "escalated": False},
                )

        # System 2: slow reasoner
        reasoner_result = await self._reasoner.run(ctx.messages)
        messages.append(reasoner_result)

        return Result(
            output=reasoner_result.content,
            messages=messages,
            metadata={"system": "reasoner", "escalated": not bool(self._classifier)},
        )
