"""RouterMiddleware: inject routing into any pattern's agent calls.

Wraps an Agent so that every call is automatically routed to the
optimal model based on task difficulty and cost.
"""

from __future__ import annotations

from pyagent_patterns.base import Agent, LLMCallable, Message

from pyagent_router.selector import Capability, ModelSelector, SelectionResult


class RoutedAgent(Agent):
    """An agent wrapper that routes each call through ModelSelector.

    The routing decision is recorded in metadata for tracing.

    Args:
        agent: The original agent.
        selector: ModelSelector to use for routing decisions.
        model_registry: Mapping of model names to LLM callables.
        required_capability: Optional capability filter for model selection.
    """

    def __init__(
        self,
        agent: Agent,
        selector: ModelSelector,
        model_registry: dict[str, LLMCallable],
        required_capability: Capability | None = None,
    ) -> None:
        super().__init__(
            name=agent.name,
            llm=agent.llm,
            system_prompt=agent.system_prompt,
            description=agent.description,
        )
        self._original_agent = agent
        self._selector = selector
        self._model_registry = model_registry
        self._required_capability = required_capability
        self.routing_log: list[SelectionResult] = []

    async def run(self, messages: list[Message]) -> Message:
        """Route the call to the optimal model, then execute."""
        # Extract task text from messages for difficulty scoring
        task_text = " ".join(m.content for m in messages if m.content)

        selection = self._selector.select(task_text, self._required_capability)
        self.routing_log.append(selection)

        # Swap LLM to the selected model if available in registry
        llm = self._model_registry.get(selection.model, self._original_agent.llm)

        # Create a temporary agent with the routed LLM
        routed = Agent(
            name=self._original_agent.name,
            llm=llm,
            system_prompt=self._original_agent.system_prompt,
            description=self._original_agent.description,
        )
        result = await routed.run(messages)

        # Attach routing metadata to the message
        result = Message(
            role=result.role,
            content=result.content,
            name=result.name,
            metadata={
                **result.metadata,
                "routed_model": selection.model,
                "difficulty": selection.difficulty.score,
                "estimated_cost": selection.cost_estimate.total_cost,
                "reason": selection.reason,
            },
        )
        return result


class RouterMiddleware:
    """Middleware that wraps agents with automatic model routing.

    Usage:
        middleware = RouterMiddleware(model_registry={"gpt-4o": my_gpt4o, "gpt-4o-mini": my_mini})
        routed_agent = middleware.wrap(my_agent)
        # routed_agent now auto-selects model per call

    Args:
        model_registry: Mapping of model names to LLM callables.
        selector: Optional ModelSelector. Created with defaults if None.
        required_capability: Optional default capability filter.
    """

    def __init__(
        self,
        model_registry: dict[str, LLMCallable],
        selector: ModelSelector | None = None,
        required_capability: Capability | None = None,
    ) -> None:
        self._registry = model_registry
        self._selector = selector or ModelSelector()
        self._capability = required_capability

    def wrap(self, agent: Agent) -> RoutedAgent:
        """Wrap an agent with routing capabilities."""
        return RoutedAgent(
            agent=agent,
            selector=self._selector,
            model_registry=self._registry,
            required_capability=self._capability,
        )

    def wrap_all(self, agents: list[Agent]) -> list[RoutedAgent]:
        """Wrap multiple agents."""
        return [self.wrap(a) for a in agents]
