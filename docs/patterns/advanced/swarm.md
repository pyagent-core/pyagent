# Swarm Pattern

Decentralised multi-agent system: agents form local views, share with neighbours across rounds, and global consensus or diversity emerges from local interaction.

**Best for:** Collective intelligence, opinion diversity, technology scanning, distributed decision-making.  
**LLM calls:** N agents × R rounds.

---

## Sequence Diagram

```mermaid
sequenceDiagram
    participant A1 as Agent 1
    participant A2 as Agent 2
    participant A3 as Agent 3

    rect rgb(230, 245, 255)
        Note over A1,A3: Round 0 — Independent positions
        A1->>A1: Form initial view
        A2->>A2: Form initial view
        A3->>A3: Form initial view
    end

    rect rgb(255, 245, 230)
        Note over A1,A3: Round 1 — Neighbour interaction
        A1->>A2: Share view
        A2->>A3: Share view
        A3->>A1: Share view
        A1->>A1: Update based on A3's view
        A2->>A2: Update based on A1's view
        A3->>A3: Update based on A2's view
    end
```

---

## Use Case 1 — Technology Trend Forecasting (Gemini)

Five independent analysts form views, share with 2 neighbours each round, and refine through interaction.

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.advanced import Swarm
from pyagent_providers import GeminiLLM

pattern = Swarm(
    agents=[
        Agent(
            "ml_researcher",
            GeminiLLM("gemini-2.5-flash"),
            system_prompt="You are an ML researcher. Form views based on ML/AI research trends: "
                          "what models, architectures, and capabilities will dominate in 2 years. "
                          "When you see a neighbour's view, update yours if their evidence is compelling.",
        ),
        Agent(
            "infra_engineer",
            GeminiLLM("gemini-2.5-flash"),
            system_prompt="You are a cloud infrastructure engineer. Form views based on platform "
                          "and infrastructure trends. Update your view when presented with "
                          "compelling evidence from colleagues.",
        ),
        Agent(
            "product_manager",
            GeminiLLM("gemini-2.5-flash"),
            system_prompt="You are a product manager tracking user adoption trends. "
                          "Focus on what users actually want vs what researchers build. "
                          "Update your view based on compelling market evidence.",
        ),
        Agent(
            "vc_analyst",
            GeminiLLM("gemini-2.5-flash"),
            system_prompt="You are a VC analyst tracking investment flows and startup activity. "
                          "Form views on where capital is flowing and why. "
                          "Update based on compelling evidence from colleagues.",
        ),
        Agent(
            "enterprise_architect",
            GeminiLLM("gemini-2.5-flash"),
            system_prompt="You are an enterprise architect tracking corporate adoption. "
                          "Focus on what enterprises are actually deploying vs piloting. "
                          "Update based on compelling evidence.",
        ),
    ],
    rounds=3,
    neighbor_count=2,
    aggregation="last",
)

result = asyncio.run(pattern.run(
    "What are the top 3 most important AI/ML technology trends for enterprise software in 2026?"
))
print(result.output)
print(f"Agents: {result.metadata['agents']}, Rounds: {result.metadata['rounds']}")
print(f"Cost: ${result.cost_estimate:.4f}")
```

---

## Use Case 2 — Collective Code Architecture Design (OpenAI + Anthropic)

```python
from pyagent_providers import OpenAILLM, AnthropicLLM

arch_swarm = Swarm(
    agents=[
        Agent(
            "backend_specialist",
            OpenAILLM("gpt-4o-mini"),
            system_prompt="You specialise in backend systems. Form an architecture view "
                          "considering scalability, data models, and API design. "
                          "Update your view when frontend or ops colleagues raise valid constraints.",
        ),
        Agent(
            "frontend_specialist",
            AnthropicLLM("claude-haiku-3-5-20241022"),
            system_prompt="You specialise in frontend systems. Form an architecture view "
                          "considering UX, state management, and build complexity. "
                          "Update when backend constraints are compelling.",
        ),
        Agent(
            "ops_specialist",
            OpenAILLM("gpt-4o-mini"),
            system_prompt="You specialise in operations and infrastructure. "
                          "Form a view considering deployment, monitoring, and reliability. "
                          "Push back on architectures that are operationally complex.",
        ),
        Agent(
            "security_specialist",
            AnthropicLLM("claude-haiku-3-5-20241022"),
            system_prompt="You specialise in application security. "
                          "Form a view considering authentication, authorisation, and data protection. "
                          "Flag security implications of colleagues' architectural choices.",
        ),
    ],
    rounds=2,
    neighbor_count=2,
    aggregation="last",
)

result = asyncio.run(arch_swarm.run(
    "Design the architecture for a multi-tenant analytics platform: "
    "100k tenants, real-time dashboards, 10TB data/day, SOC2 compliance required."
))
```

---

## Use Case 3 — Multi-Provider Consensus (LiteLLM)

Use different providers to prevent any single model's biases from dominating.

```python
from pyagent_providers import LiteLLM

diverse_swarm = Swarm(
    agents=[
        Agent(f"analyst_openai", LiteLLM("gpt-4o-mini"),
              system_prompt="Form and refine your analysis. Update when neighbours make compelling points."),
        Agent(f"analyst_anthropic", LiteLLM("anthropic/claude-haiku-3.5"),
              system_prompt="Form and refine your analysis. Update when neighbours make compelling points."),
        Agent(f"analyst_gemini", LiteLLM("gemini/gemini-2.5-flash"),
              system_prompt="Form and refine your analysis. Update when neighbours make compelling points."),
    ],
    rounds=2,
    neighbor_count=2,
    aggregation="consensus",
)

result = asyncio.run(diverse_swarm.run(
    "Should an AI startup prioritise getting to market fast with GPT-4 "
    "or spend 6 months building proprietary fine-tuned models?"
))
```

---

## OTel Trace Output

```
Trace: pyagent.pattern.swarm (8.2s, $0.021)
├── Round 0 — independent
│   ├── pyagent.agent.ml_researcher (1.4s)
│   ├── pyagent.agent.infra_engineer (1.3s)
│   ├── pyagent.agent.product_manager (1.2s)
│   ├── pyagent.agent.vc_analyst (1.1s)
│   └── pyagent.agent.enterprise_architect (1.4s)
├── Round 1 — neighbour exchange [neighbor_count=2]
│   └── [parallel updates with neighbour context]
├── Round 2 — neighbour exchange
│   └── [parallel updates]
└── aggregation: last → final swarm output
```

---

## When to Use

| Condition | Recommendation |
|---|---|
| You want emergent collective intelligence | ✅ Use Swarm |
| Diverse independent starting positions add value | ✅ Use Swarm |
| Agents need a central coordinator | ❌ Use Orchestrator-Workers |
| Agents don't interact with each other | ❌ Use Fan-Out/Fan-In |
| Fixed roles with structured rounds | ❌ Use Role-Based |

---

## See Also

- [Fan-Out / Fan-In](../orchestration/fan-out-fan-in.md) — independent parallel agents without peer interaction
- [Role-Based](../structural/role-based.md) — structured role collaboration vs emergent peer interaction
- [Debate](../resolution/debate.md) — adversarial positions with a judge
