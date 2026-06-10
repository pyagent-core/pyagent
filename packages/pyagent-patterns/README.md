# pyagent-patterns

**18 reusable multi-agent orchestration patterns for LLMs** — zero dependencies, async-first, fully typed.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-patterns
```

No mandatory dependencies. Bring your own LLM.

---

## Pattern Catalog

| Tier | Pattern | LLM Calls | Best For |
|---|---|---|---|
| **Orchestration** | Supervisor | 2–3 | Task routing, customer support |
| | Pipeline | N | Sequential processing, ETL |
| | Fan-Out/Fan-In | N+1 | Parallel analysis, research |
| | Hierarchical | 1+T+W | Enterprise workflows |
| | Orchestrator-Workers | 1+N+1 | Dynamic task decomposition |
| **Resolution** | Self-Reflection | 2–6 | Code gen, writing quality |
| | Cross-Reflection | 3–6 | Peer review, editing |
| | Debate | D×R+1 | High-stakes decisions |
| | Voting | N | Consensus, fault tolerance |
| | Evaluator-Optimizer | 2–6 | Criteria-driven quality |
| **Structural** | Role-Based | N×rounds | Team simulation |
| | Layered | sum(agents) | Multi-level analysis |
| | Topology | varies | Communication structure |
| | Blackboard | N×rounds | Shared state coordination |
| **Advanced** | Talker-Reasoner | 1–3 | Cost-optimized chat |
| | Swarm | N×rounds | Emergent behavior |
| | Human-in-the-Loop | 1+ | Safety-critical tasks |
| | ReAct | 1–N | Tool-using agents |

Plus: **PatternAdvisor** (auto-select pattern), **GuardrailChain** (PII/length/content guards), **BoundedExecution** (retry + fallback), **CircuitBreaker** (cascading failure prevention).

---

## Connecting your LLM

PyAgent has no provider dependencies. Every pattern accepts any object satisfying the `LLMCallable` protocol:

```python
class LLMCallable(Protocol):
    async def __call__(self, messages: list[Message]) -> str: ...
```

### OpenAI

```python
from openai import AsyncOpenAI
from pyagent_patterns.base import Message

class OpenAILLM:
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def __call__(self, messages: list[Message]) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role.value, "content": m.content} for m in messages],
        )
        return response.choices[0].message.content or ""
```

### Anthropic

```python
import anthropic
from pyagent_patterns.base import Message, Role

class AnthropicLLM:
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def __call__(self, messages: list[Message]) -> str:
        system = next(
            (m.content for m in messages if m.role == Role.SYSTEM),
            "You are a helpful assistant.",
        )
        chat_msgs = [
            {"role": m.role.value, "content": m.content}
            for m in messages if m.role != Role.SYSTEM
        ]
        response = await self._client.messages.create(
            model=self._model, max_tokens=4096,
            system=system, messages=chat_msgs,
        )
        return response.content[0].text
```

### MockLLM (testing, no API keys)

```python
from pyagent_patterns.base import MockLLM

# Returns responses in order, cycling when exhausted
llm = MockLLM(responses=["Step 1 output", "Step 2 output", "Final answer"])
llm = MockLLM(responses=["response"], delay=0.1)  # optional simulated latency
llm = MockLLM()                                    # echo mode — repeats last user message
```

---

## Core Concepts

```python
import asyncio
from pyagent_patterns.base import Agent, Message, Context, Result

agent = Agent(
    name="analyst",
    llm=OpenAILLM("gpt-4o-mini"),
    system_prompt="You are a senior financial analyst. Be precise and cite data.",
)

# Run any pattern the same way
result: Result = asyncio.run(pattern.run("Your task here"))

result.output            # str — final text output
result.messages          # list[Message] — all messages generated
result.metadata          # dict — pattern-specific data (rounds, route, scores, etc.)
result.duration_seconds  # float — wall-clock time
result.token_estimate    # int — rough total token count
result.cost_estimate     # float — rough cost in USD

# Chain patterns with shared context
ctx = Context(task="original task", metadata={"session_id": "abc123"})
result = asyncio.run(pattern.run("follow-up task", context=ctx))
```

---

## Pattern Examples

### Pipeline — sequential chain

```python
import asyncio
from pyagent_patterns.orchestration import Pipeline

pipeline = Pipeline(stages=[
    Agent("extractor", AnthropicLLM("claude-haiku-3-5-20241022"),
          system_prompt="Extract every claim, figure, and named entity. Be exhaustive."),
    Agent("fact_checker", OpenAILLM("gpt-4o-mini"),
          system_prompt="Identify which items are verifiable facts vs opinions."),
    Agent("writer", AnthropicLLM("claude-sonnet-4-20250514"),
          system_prompt="Write a concise, structured brief. Lead with the most important fact."),
])

result = asyncio.run(pipeline.run("Tesla Q3 2025 earnings: Revenue $25.2B (+8% YoY)..."))
# metadata: {"stages": 3, "stage_names": ["extractor", "fact_checker", "writer"]}
```

### Self-Reflection — generate → critique → refine

```python
from pyagent_patterns.resolution import SelfReflection

self_reflection = SelfReflection(
    agent=Agent("coder", OpenAILLM("gpt-4o-mini"),
                system_prompt="Write production-quality Python with type hints and error handling."),
    critic=Agent("reviewer", OpenAILLM("gpt-4o"),
                 system_prompt="Review strictly for correctness, error handling, and PEP 8. "
                               "If production-ready, respond with 'APPROVED'."),
    max_rounds=3,
    stop_phrase="APPROVED",
)

result = asyncio.run(self_reflection.run(
    "Write an async function that retries HTTP requests with exponential backoff and jitter."
))
# metadata: {"rounds": 2, "max_rounds": 3, "early_stop": True}
```

### Fan-Out/Fan-In — parallel + aggregate

```python
from pyagent_patterns.orchestration import FanOutFanIn

analysis = FanOutFanIn(
    agents=[
        Agent("bull",    GeminiLLM("gemini-2.5-flash"), system_prompt="Argue the strongest bullish case."),
        Agent("bear",    GeminiLLM("gemini-2.5-flash"), system_prompt="Argue the strongest bearish case."),
        Agent("neutral", GeminiLLM("gemini-2.5-flash"), system_prompt="Give a balanced assessment."),
    ],
    aggregator=Agent("analyst", GeminiLLM("gemini-2.5-pro"),
                     system_prompt="Synthesise into a structured investment memo."),
)

result = asyncio.run(analysis.run("Investment thesis for Nvidia at current valuation"))
# metadata: {"parallel_agents": 3, "agent_names": ["bull", "bear", "neutral"]}
```

---

## Pattern Composition

Every pattern implements the same base class, so any pattern can be used anywhere an `Agent` is expected:

```python
from pyagent_patterns.orchestration import Pipeline, FanOutFanIn
from pyagent_patterns.resolution import SelfReflection

# Nest FanOut of Pipelines, wrapped in SelfReflection
web_pipeline = Pipeline(stages=[
    Agent("web_searcher",  OpenAILLM("gpt-4o-mini"), system_prompt="Search the web for sources."),
    Agent("web_extractor", OpenAILLM("gpt-4o-mini"), system_prompt="Extract key claims."),
])
db_pipeline = Pipeline(stages=[
    Agent("db_querier",   AnthropicLLM("claude-haiku-3-5-20241022"), system_prompt="Query knowledge base."),
    Agent("db_formatter", AnthropicLLM("claude-haiku-3-5-20241022"), system_prompt="Format results."),
])

research = FanOutFanIn(
    agents=[web_pipeline, db_pipeline],
    aggregator=Agent("synthesiser", OpenAILLM("gpt-4o"), system_prompt="Synthesise all sources."),
)

final = SelfReflection(
    agent=research,
    critic=Agent("critic", OpenAILLM("gpt-4o"),
                 system_prompt="Check for gaps. If complete, respond with 'APPROVED'."),
    max_rounds=2,
)
```

---

## Pattern Advisor

Not sure which pattern to use? Describe your task and constraints:

```python
from pyagent_patterns.advisor import PatternAdvisor, Constraints, Quality, Latency

advisor = PatternAdvisor()

rec = advisor.recommend(
    "Write and iteratively refine a technical guide on distributed transactions",
    Constraints(quality=Quality.HIGH)
)
print(rec.pattern)               # "self_reflection"
print(rec.reason)                # "High quality task → generate-critique-refine loop"
print(rec.estimated_calls)       # 4
print(rec.estimated_cost_range)  # "$0.004-0.012"
print(rec.alternatives)          # ["cross_reflection", "evaluator_optimizer"]
```

---

## Guardrails

Four insertion points: input validation, inter-agent, tool-call, and output validation.

```python
from pyagent_patterns.guardrails import GuardrailChain, PIIGuard, LengthGuard, ContentGuard

# Chain multiple guards — all must pass, sanitized content flows through
chain = GuardrailChain([
    PIIGuard(redact=True),                                        # redact emails, phones, SSNs
    LengthGuard(max_chars=3000, truncate=True),                   # enforce output length
    ContentGuard(deny_words=["confidential", "internal roadmap"]),# block forbidden terms
])

result = chain.check(agent_output)
if result.passed:
    safe_output = result.sanitized_content or agent_output
else:
    print(f"Guardrail blocked: {result.message}")
```

---

## Recovery

```python
from pyagent_patterns.recovery import BoundedExecution, CircuitBreaker

# retry → fallback → graceful degradation
bounded = BoundedExecution(
    pattern=Pipeline(stages=[Agent("primary", OpenAILLM("gpt-4o"), system_prompt="...")]),
    fallback=Pipeline(stages=[Agent("backup", AnthropicLLM("claude-haiku-3-5-20241022"), system_prompt="...")]),
    max_retries=2,
    timeout_seconds=30.0,
    max_tokens=50_000,
)

result = asyncio.run(bounded.run("Complex analysis task"))
print(result.metadata["recovery_level"])   # 0 = primary | 1 = fallback | 2 = degraded

# Circuit breaker — prevent cascading failures
circuit = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=60.0,
                         fallback_result="[Service temporarily unavailable.]")
result = asyncio.run(circuit.execute(my_pattern, "task"))
print(circuit.state)   # CircuitState.CLOSED | OPEN | HALF_OPEN
```

---

## When to Use Which Pattern

| If you need to… | Pattern |
|---|---|
| Route requests to domain specialists | **Supervisor** |
| Run a fixed sequence of steps | **Pipeline** |
| Get multiple independent perspectives fast | **Fan-Out/Fan-In** |
| Delegate to a fixed team hierarchy | **Hierarchical** |
| Dynamically plan and assign subtasks | **Orchestrator-Workers** |
| Iteratively improve via self-critique | **Self-Reflection** |
| Get independent peer review | **Cross-Reflection** |
| Make a high-stakes adversarial decision | **Debate** |
| Reduce variance with ensemble answers | **Voting** |
| Meet explicit quality criteria with scoring | **Evaluator-Optimizer** |
| Simulate a team with defined roles | **Role-Based** |
| Process data through abstraction layers | **Layered** |
| Control information flow topology | **Topology** |
| Decouple agents via shared state | **Blackboard** |
| Save cost on mixed-complexity queries | **Talker-Reasoner** |
| Explore solutions with emergent consensus | **Swarm** |
| Require human approval at key steps | **Human-in-the-Loop** |
| Use external tools, search, or APIs | **ReAct** |

---

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference, all 18 pattern examples, and integration guides.
