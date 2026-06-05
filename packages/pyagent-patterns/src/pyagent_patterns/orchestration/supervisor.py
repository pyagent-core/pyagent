"""Supervisor pattern: classify input → route to specialist agent → collect result.

The Supervisor inspects the incoming task, classifies it into a category,
dispatches to the appropriate specialist agent, and optionally formats
the final response.

LLM calls: 2-3 (classify + specialist + optional format)
"""

from __future__ import annotations

from pyagent_patterns.base import Agent, Context, Message, Pattern, Result


class Supervisor(Pattern):
    """Classify → route → collect orchestration pattern.

    Args:
        classifier: Agent that classifies the task into a route key.
        routes: Mapping of route keys to specialist agents.
        formatter: Optional agent that formats the final response.
        default_route: Key to use when classification doesn't match any route.
    """

    def __init__(
        self,
        classifier: Agent,
        routes: dict[str, Agent],
        formatter: Agent | None = None,
        default_route: str | None = None,
    ) -> None:
        self._classifier = classifier
        self._routes = routes
        self._formatter = formatter
        self._default_route = default_route

    @property
    def pattern_type(self) -> str:
        return "supervisor"

    async def _execute(self, ctx: Context) -> Result:
        messages: list[Message] = []

        # Step 1: Classify the task
        classify_prompt = (
            f"Classify the following task into exactly one of these categories: "
            f"{', '.join(self._routes.keys())}.\n"
            f"Respond with ONLY the category name, nothing else.\n\n"
            f"Task: {ctx.task}"
        )
        classify_msg = Message.user(classify_prompt)
        classification = await self._classifier.run([classify_msg])
        messages.append(classification)

        # Step 2: Route to specialist
        route_key = classification.content.strip().lower()
        agent = self._routes.get(route_key)
        if agent is None and self._default_route:
            agent = self._routes.get(self._default_route)
            route_key = self._default_route
        if agent is None:
            # Fallback: use first available route
            route_key = next(iter(self._routes))
            agent = self._routes[route_key]

        specialist_msg = await agent.run(ctx.messages)
        messages.append(specialist_msg)

        # Step 3: Optional formatting
        output = specialist_msg.content
        if self._formatter:
            format_msgs = [
                Message.user(
                    f"Format the following response for the user:\n\n{specialist_msg.content}"
                )
            ]
            formatted = await self._formatter.run(format_msgs)
            messages.append(formatted)
            output = formatted.content

        return Result(
            output=output,
            messages=messages,
            metadata={
                "route_key": route_key,
                "classifier_output": classification.content,
            },
        )
