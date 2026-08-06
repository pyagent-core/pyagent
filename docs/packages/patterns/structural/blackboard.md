---
description: "The Blackboard pattern in PyAgent — agents read and write a shared knowledge store asynchronously. Use it for opportunistic, emergent collaboration around shared state."
---

# Blackboard Pattern

Agents communicate indirectly via a shared, asynchronous state store. Each agent reads specific keys and writes its outputs back — no direct messaging.

**Best for:** Financial intelligence, data enrichment pipelines, multi-expert analysis where outputs feed each other.  
**LLM calls:** N agents × R rounds.

---

## Sequence Diagram

```mermaid
sequenceDiagram
    participant BB as Blackboard
    participant A as Alpha Agent
    participant R as Risk Agent
    participant P as Portfolio Agent

    BB->>A: reads: [task]
    A->>BB: writes: alpha_signals
    BB->>R: reads: [task, alpha_signals]
    R->>BB: writes: risk_metrics
    BB->>P: reads: [alpha_signals, risk_metrics]
    P->>BB: writes: portfolio_weights
```

---

## Use Case 1 — Financial Portfolio Construction (OpenAI)

Agents chain through the blackboard — each builds on the previous agent's committed state.

=== "Python"

    ```python
    import asyncio
    from pyagent_patterns.base import Agent
    from pyagent_patterns.structural import Blackboard
    from pyagent_patterns.structural.blackboard import BlackboardAgent
    from pyagent_providers import OpenAILLM

    pattern = Blackboard(
        agents=[
            BlackboardAgent(
                agent=Agent(
                    "alpha_generator",
                    OpenAILLM("gpt-4o"),
                    system_prompt="Generate alpha signals for each asset in the watchlist. "
                                  "For each asset: state direction (long/short/neutral), "
                                  "conviction (high/medium/low), and 2-sentence rationale. "
                                  "Format as structured data.",
                ),
                reads=["task"],
                writes=["alpha_signals"],
            ),
            BlackboardAgent(
                agent=Agent(
                    "risk_manager",
                    OpenAILLM("gpt-4o"),
                    system_prompt="Given the alpha signals, assess portfolio-level risk: "
                                  "calculate correlation exposure, sector concentration, "
                                  "tail risk scenarios, and max position sizes. "
                                  "Recommend position limits for each asset.",
                ),
                reads=["task", "alpha_signals"],
                writes=["risk_metrics"],
            ),
            BlackboardAgent(
                agent=Agent(
                    "portfolio_optimizer",
                    OpenAILLM("gpt-4o"),
                    system_prompt="Given alpha signals AND risk constraints, "
                                  "construct the optimal portfolio allocation. "
                                  "Respect position limits. Maximize risk-adjusted return. "
                                  "Output allocation as percentages summing to 100%.",
                ),
                reads=["alpha_signals", "risk_metrics"],
                writes=["portfolio_weights"],
            ),
            BlackboardAgent(
                agent=Agent(
                    "order_generator",
                    OpenAILLM("gpt-4o-mini"),
                    system_prompt="Given the portfolio weights, "
                                  "generate execution orders: asset, direction, size, "
                                  "and suggested order type (market/limit). "
                                  "Flag any large moves that need staged execution.",
                ),
                reads=["portfolio_weights", "risk_metrics"],
                writes=["trade_orders"],
            ),
        ],
        rounds=1,
    )

    result = asyncio.run(pattern.run(
        "Watchlist: NVDA, MSFT, AMZN, META, GOOGL. "
        "Portfolio size: $10M. Max single position: 25%. "
        "Optimize for risk-adjusted return over 3-month horizon."
    ))
    print(result.output)
    print("Final blackboard state:")
    for key, value in result.metadata["final_state"].items():
        print(f"  [{key}]: {str(value)[:80]}...")
    print(f"Cost: ${result.cost_estimate:.4f}")
    ```

=== "Blueprint YAML"

    Declare the same blackboard chain as a `pyagent-blueprint` manifest:

    ```yaml
    api_version: pyagent/v1
    metadata:
      name: portfolio-blackboard
      version: 1.0.0
      description: Agents chain through a shared blackboard — each builds on prior committed state
    providers:
      primary: { model: gpt-4o }
    agents:
      alpha_generator: { provider: primary, prompt: "Generate alpha signals for each asset." }
      risk_manager: { provider: primary, prompt: "Assess portfolio risk given the alpha signals." }
      portfolio_optimizer: { provider: primary, prompt: "Construct the optimal allocation given signals and risk." }
    workflows:
      construct:
        pattern: blackboard
        agents:
          agents:
            - { agent: alpha_generator, reads: [task], writes: [alpha_signals] }
            - { agent: risk_manager, reads: [task, alpha_signals], writes: [risk_metrics] }
            - { agent: portfolio_optimizer, reads: [alpha_signals, risk_metrics], writes: [portfolio_weights] }
    ```

    ```bash
    pyagent-blueprint validate portfolio-blackboard.yaml
    pyagent-blueprint test portfolio-blackboard.yaml
    ```

---

## Use Case 2 — Competitive Intelligence Pipeline (Anthropic + Gemini)

Each specialist enriches the shared knowledge base before the synthesizer runs.

```python
from pyagent_providers import AnthropicLLM, GeminiLLM

intelligence = Blackboard(
    agents=[
        BlackboardAgent(
            agent=Agent(
                "product_analyst",
                GeminiLLM("gemini-2.5-flash"),
                system_prompt="Analyze the competitor's product: features, pricing, "
                              "UX, and technical capabilities. Extract structured data.",
            ),
            reads=["task"],
            writes=["product_analysis"],
        ),
        BlackboardAgent(
            agent=Agent(
                "market_analyst",
                GeminiLLM("gemini-2.5-flash"),
                system_prompt="Analyze market position: market share, customer segments, "
                              "GTM strategy, and partnerships.",
            ),
            reads=["task"],
            writes=["market_analysis"],
        ),
        BlackboardAgent(
            agent=Agent(
                "strategic_analyst",
                AnthropicLLM("claude-sonnet-4-20250514"),
                system_prompt="Given both product and market analyses, "
                              "identify competitive gaps we can exploit, "
                              "threats to our position, and strategic recommendations.",
            ),
            reads=["product_analysis", "market_analysis"],
            writes=["strategic_assessment"],
        ),
        BlackboardAgent(
            agent=Agent(
                "report_writer",
                AnthropicLLM("claude-sonnet-4-20250514"),
                system_prompt="Write an executive competitive intelligence report "
                              "from all available analyses. Include: "
                              "Executive Summary, Key Threats, Opportunities, Recommended Actions.",
            ),
            reads=["product_analysis", "market_analysis", "strategic_assessment"],
            writes=["final_report"],
        ),
    ],
    rounds=1,
)

result = asyncio.run(intelligence.run("Competitor analysis: Salesforce Einstein AI"))
print(result.metadata["final_state"]["final_report"])
```

---

## OTel Trace Output

```
Trace: pyagent.pattern.blackboard (6.8s, $0.022)
├── Round 1
│   ├── pyagent.agent.alpha_generator (2.1s, gpt-4o)
│   │   └── writes: alpha_signals
│   ├── pyagent.agent.risk_manager (1.9s, gpt-4o) [reads: alpha_signals]
│   │   └── writes: risk_metrics
│   ├── pyagent.agent.portfolio_optimizer (1.6s, gpt-4o) [reads: alpha_signals, risk_metrics]
│   │   └── writes: portfolio_weights
│   └── pyagent.agent.order_generator (1.2s, gpt-4o-mini) [reads: portfolio_weights, risk_metrics]
│       └── writes: trade_orders
└── final_state: {alpha_signals: ..., risk_metrics: ..., portfolio_weights: ..., trade_orders: ...}
```

---

## When to Use

| Condition | Recommendation |
|---|---|
| Agents need to share and build on each other's outputs | ✅ Use Blackboard |
| Output dependencies are complex (A→C, B→C, both→D) | ✅ Use Blackboard |
| A central coordinator routes all communication | ❌ Use Orchestrator-Workers |
| Sequential stages with no shared state | ❌ Use Pipeline |
| Agents communicate directly with neighbors | ❌ Use Swarm |

---

<!-- gen:cookbooks:start (generated by scripts/gen_docs.py from docs/cookbook/ — do not edit by hand) -->
## Cookbook recipes

Complete, runnable examples that use the **Blackboard** pattern:

| Recipe | Domain | What it does | Complexity |
|--------|--------|--------------|------------|
| [Emergent NPC World](../../../cookbook/gaming/npc-world.md) | Gaming & Simulation | NPC agents read/write a shared world-state blackboard for emergent behavior | Advanced |
<!-- gen:cookbooks:end -->

## See Also

- [Orchestrator-Workers](../orchestration/orchestrator-workers.md) — central coordinator, not shared state
- [Swarm](../advanced/swarm.md) — peer-to-peer agent communication
- [Layered](layered.md) — layered processing without persistent shared state

---

<!-- pattern-mesh:start -->

## Explore all design patterns

**Orchestration:** [Supervisor](../orchestration/supervisor.md) · [Pipeline](../orchestration/pipeline.md) · [Fan-Out / Fan-In](../orchestration/fan-out-fan-in.md) · [Hierarchical](../orchestration/hierarchical.md) · [Orchestrator-Workers](../orchestration/orchestrator-workers.md)  
**Resolution:** [Self-Reflection](../resolution/self-reflection.md) · [Cross-Reflection](../resolution/cross-reflection.md) · [Debate](../resolution/debate.md) · [Voting](../resolution/voting.md) · [Evaluator-Optimizer](../resolution/evaluator-optimizer.md)  
**Structural:** [Role-Based](../structural/role-based.md) · [Layered](../structural/layered.md) · [Topology](../structural/topology.md) · **Blackboard**  
**Iterative & Advanced:** [ReAct](../advanced/react.md) · [Talker-Reasoner](../advanced/talker-reasoner.md) · [Swarm](../advanced/swarm.md) · [Human-in-the-Loop](../advanced/human-in-the-loop.md)  

[Browse the full pattern catalog →](../index.md)

<!-- pattern-mesh:end -->
