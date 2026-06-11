# Guardrails Guide

Validate, sanitize, and block agent inputs and outputs before they cause downstream problems. `pyagent-patterns` ships four built-in guardrails and a composable chain — no extra package needed.

```python
from pyagent_patterns.guardrails import GuardrailChain, LengthGuard, PIIGuard, ContentGuard
```

---

## Why Guardrails Matter

LLM inputs and outputs can contain PII, exceed context limits, or include unsafe content. In multi-agent systems these problems compound — a 50,000-token output from stage 1 will blow up stage 2's context, and unredacted PII passed between agents gets logged by every one of them.

Guardrails give you a single enforcement point at each boundary.

---

## Built-in Guards

### LengthGuard

Reject or truncate messages that exceed a character limit.

```python
from pyagent_patterns.guardrails import LengthGuard

# Hard reject — raises if too long
strict = LengthGuard(max_chars=5000)
result = strict.check("x" * 6000)
print(result.passed)   # False
print(result.message)  # "Message exceeds 5000 chars (6000)"

# Soft truncate — passes but shortens
lenient = LengthGuard(max_chars=5000, truncate=True)
result = lenient.check("x" * 6000)
print(result.passed)              # True
print(len(result.sanitized_content))  # 5000
```

### PIIGuard

Detect and redact emails, phone numbers, SSNs, and credit card numbers.

```python
from pyagent_patterns.guardrails import PIIGuard

# Redact mode (default: keeps message, replaces PII)
guard = PIIGuard(redact=True)
result = guard.check("Contact jane@example.com or call 555-867-5309")
print(result.sanitized_content)
# "Contact [REDACTED-EMAIL] or call [REDACTED-PHONE]"

# Reject mode (block the message entirely if PII found)
strict = PIIGuard(redact=False)
result = strict.check("My SSN is 123-45-6789")
print(result.passed)   # False
print(result.message)  # "PII detected: ssn"
```

Detected PII types: `email`, `phone`, `ssn`, `credit_card`.

### ContentGuard

Block messages containing deny-listed words or regex patterns.

```python
from pyagent_patterns.guardrails import ContentGuard

# Exact word matching (case-insensitive)
guard = ContentGuard(deny_words=["password", "secret_key", "api_key"])
result = guard.check("Here is my api_key: sk-abc123")
print(result.passed)   # False
print(result.message)  # "Blocked content detected: api_key"

# Regex patterns for more flexibility
import re
guard = ContentGuard(deny_patterns=[
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),   # OpenAI key pattern
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),   # GitHub token pattern
])
```

### GuardrailChain

Run multiple guards in sequence — stops at the first failure.

```python
from pyagent_patterns.guardrails import GuardrailChain, LengthGuard, PIIGuard, ContentGuard

chain = GuardrailChain([
    LengthGuard(max_chars=10_000, truncate=True),   # truncate first
    PIIGuard(redact=True),                           # then redact PII
    ContentGuard(deny_words=["secret", "password"]), # then check content
])

result = chain.check("My email is alice@corp.com and my password is hunter2")
# After truncation (if needed) → PII redacted → content check
print(result.sanitized_content)
# "My email is [REDACTED-EMAIL] and my [BLOCKED] is [BLOCKED]"
```

---

## Integration Patterns

### Input + Output Validation

The most common pattern: guard the user's message before it enters the system, and guard the final output before it reaches the user.

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.guardrails import GuardrailChain, PIIGuard, LengthGuard
from pyagent_providers import AnthropicLLM

input_guard  = GuardrailChain([LengthGuard(max_chars=5000), PIIGuard(redact=True)])
output_guard = GuardrailChain([LengthGuard(max_chars=20_000, truncate=True)])

pipeline = Pipeline(stages=[
    Agent("analyst",  AnthropicLLM("claude-haiku-3-5-20241022")),
    Agent("writer",   AnthropicLLM("claude-sonnet-4-20250514")),
])

async def run_safe(user_input: str) -> str:
    # Validate input
    check = input_guard.check(user_input)
    if not check.passed:
        return f"Input rejected: {check.message}"
    safe_input = check.sanitized_content or user_input

    # Run pipeline
    result = await pipeline.run(safe_input)

    # Validate output
    out_check = output_guard.check(result.output)
    return out_check.sanitized_content or result.output

print(asyncio.run(run_safe("Summarise these notes: ...")))
```

### Inter-Agent Guardrail

In a pipeline, guard the output of each stage before it becomes the next stage's input. Useful when early stages produce verbose or sensitive outputs.

```python
from pyagent_patterns.guardrails import GuardrailChain, LengthGuard, PIIGuard

inter_agent_guard = GuardrailChain([
    LengthGuard(max_chars=8_000, truncate=True),
    PIIGuard(redact=True),
])

async def guarded_pipeline(text: str) -> str:
    r1 = await extractor_agent.run(text)
    safe = inter_agent_guard.check(r1.output).sanitized_content or r1.output

    r2 = await analyst_agent.run(safe)
    safe = inter_agent_guard.check(r2.output).sanitized_content or r2.output

    r3 = await writer_agent.run(safe)
    return r3.output
```

### Guardrails with Fan-Out

Guard each parallel agent's output before the aggregator sees it.

```python
import asyncio
from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_patterns.guardrails import GuardrailChain, LengthGuard

guard = GuardrailChain([LengthGuard(max_chars=3_000, truncate=True)])

fanout = FanOutFanIn(
    agents=[bull_agent, bear_agent, macro_agent],
    aggregator=synthesis_agent,
)

async def run_guarded_fanout(task: str) -> str:
    result = await fanout.run(task)
    # Guard the aggregated output
    final = guard.check(result.output)
    return final.sanitized_content or result.output
```

---

## Custom Guardrails

Implement the `Guardrail` protocol to add your own logic.

```python
from dataclasses import dataclass
from pyagent_patterns.guardrails import GuardrailChain

@dataclass
class GuardrailResult:
    passed: bool
    message: str = ""
    sanitized_content: str | None = None

class LanguageGuard:
    """Block messages not written in English."""

    def check(self, content: str) -> GuardrailResult:
        # Simple heuristic: flag if > 30% non-ASCII
        non_ascii = sum(1 for c in content if ord(c) > 127)
        if len(content) > 0 and non_ascii / len(content) > 0.3:
            return GuardrailResult(passed=False, message="Non-English content detected")
        return GuardrailResult(passed=True)


class JSONOutputGuard:
    """Ensure output is valid JSON."""

    def check(self, content: str) -> GuardrailResult:
        import json
        try:
            json.loads(content)
            return GuardrailResult(passed=True)
        except json.JSONDecodeError as e:
            return GuardrailResult(passed=False, message=f"Invalid JSON: {e}")


# Compose with built-ins
chain = GuardrailChain([
    LengthGuard(max_chars=5000),
    LanguageGuard(),
    JSONOutputGuard(),
])
```

---

## Guardrails in Production

### Logging Blocked Requests

```python
import logging

logger = logging.getLogger(__name__)

async def run_with_logging(user_input: str) -> str:
    check = input_guard.check(user_input)
    if not check.passed:
        logger.warning("Guardrail blocked input", extra={
            "reason": check.message,
            "input_length": len(user_input),
        })
        return "Sorry, I can't process that request."
    return await pipeline.run(check.sanitized_content or user_input)
```

### Metrics

Track block rates to tune your thresholds:

```python
from collections import Counter

block_counts: Counter = Counter()

def guarded_check(guard: GuardrailChain, content: str):
    result = guard.check(content)
    if not result.passed:
        block_counts[result.message] += 1
    return result
```

---

## Guard Selection Reference

| Scenario | Guard | Mode |
|----------|-------|------|
| User inputs that might be too long | `LengthGuard` | truncate |
| Agent-to-agent messages | `LengthGuard` | truncate |
| Customer-facing apps | `PIIGuard` | redact |
| Internal audit logging | `PIIGuard` | reject |
| Prompts containing credentials | `ContentGuard` | deny_words |
| Structured output stages | custom `JSONOutputGuard` | reject |
| Multi-layer production system | `GuardrailChain` | all of the above |

---

## See Also

- [Recovery Guide](recovery.md) — handle failures when guardrails reject at runtime
- [Patterns Package](../packages/patterns.md) — `Agent`, `Pipeline`, `FanOutFanIn` integration points
- [API Reference](../api/patterns.md)
