# Cross-Reflection Pattern

Generator produces output, a separate reviewer provides feedback for revision.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant G as Generator
    participant R as Reviewer

    U->>G: "Write a blog post"
    G-->>R: Draft blog post
    R-->>G: "Needs stronger intro"
    G-->>R: Revised draft
    R-->>G: "APPROVED"
    G-->>U: Final polished post
```

## Code Example

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import CrossReflection

pattern = CrossReflection(
    generator=Agent("writer", MockLLM(responses=["Draft post...", "Revised with strong intro..."])),
    reviewer=Agent("editor", MockLLM(responses=["Needs stronger introduction", "APPROVED"])),
    max_rounds=3,
)

result = asyncio.run(pattern.run("Write a blog post about AI safety"))
print(f"Rounds: {result.metadata['rounds']}")
```

## When to Use

- ✅ **Use when:** External review perspective adds value
- ✅ **Use when:** Reviewer has different expertise than generator
- ❌ **Avoid when:** Speed matters more than quality
