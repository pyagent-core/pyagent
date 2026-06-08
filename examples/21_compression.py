"""Example: Compression — reduce inter-agent token transfer."""

from pyagent_compress import AgentPruner, MessageCompressor, TokenBudget
from pyagent_patterns.base import Message, Role


def main():
    # Compress verbose LLM output
    compressor = MessageCompressor(target_ratio=0.5)
    verbose_text = (
        "Let me think about this carefully. Basically, the analysis shows that "
        "revenue increased by 15% year-over-year. The data indicates a strong "
        "upward trend in Q3 earnings. In other words, the company is performing "
        "well above market expectations. It's worth noting that the profit margin "
        "expanded to 23%, which is significant compared to the industry average. "
        "The conclusion is that this represents a solid buy opportunity."
    )
    result = compressor.compress(verbose_text)
    print(f"Original: {result.original_tokens} tokens")
    print(f"Compressed: {result.compressed_tokens} tokens")
    print(f"Savings: {result.savings_pct:.0%}")
    print(f"Compressed text: {result.compressed}\n")

    # Token budget management
    budget = TokenBudget(workflow_limit=10_000, per_agent_limit=3_000, strict=False)
    budget.consume("analyst", 1500)
    budget.consume("writer", 2000)
    print(f"Budget summary: {budget.summary()}\n")

    # Agent pruning
    pruner = AgentPruner(min_contribution=0.3)
    messages = [
        Message(role=Role.ASSISTANT, content="Unique analysis of market trends and data", name="analyst"),
        Message(role=Role.ASSISTANT, content="Unique analysis of market trends and data", name="copycat"),
        Message(role=Role.ASSISTANT, content="Different risk assessment with new data points", name="risk"),
    ]
    scores = pruner.score_agents(messages, "analyze market trends")
    to_prune = pruner.should_prune(scores)
    print(f"Agent scores: {[(s.agent_name, f'{s.score:.2f}') for s in scores]}")
    print(f"Should prune: {to_prune}")

if __name__ == "__main__":
    main()
