---
description: "How to build a multi-agent code review system in Python with PyAgent — iterative peer review, security scanning, and human escalation."
summary: "Iterative review + security scan with a human gate"
complexity: Advanced
tags:
  - "Domain: Software Engineering"
  - "Pattern: Cross-Reflection"
  - "Pattern: Pipeline"
  - "Pattern: Human-in-the-Loop"
  - "Package: pyagent-patterns"
  - "Package: pyagent-router"
---

# How to Build a Multi-Agent Code Review System in Python

A production-grade multi-agent code review system that automatically guards inputs, performs iterative peer review, scans for security issues, and routes to human reviewers when needed.

**Patterns used:** CrossReflection, Pipeline, HumanInTheLoop, GuardrailChain, RouterMiddleware

---

## Architecture

```mermaid
sequenceDiagram
    participant D as Developer
    participant G as Input Guardrails
    participant C as Code Agent
    participant R as Review Agent
    participant S as Security Agent
    participant H as Human (if needed)

    D->>G: Submit code
    G->>G: Length check, PII scan
    G->>C: Sanitized code
    C->>R: Initial review
    R->>C: Feedback (up to 3 rounds)
    C->>R: Revised code
    R-->>S: APPROVED
    S->>S: Vulnerability scan
    S-->>D: Final report
    Note over S,H: If security score < 8, escalate to human
```

---

## Implementation

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.resolution import CrossReflection
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.advanced import HumanInTheLoop
from pyagent_patterns.composite import CompositePattern
from pyagent_patterns.guardrails import GuardrailChain, LengthGuard, PIIGuard, ContentGuard
from pyagent_router.middleware import RouterMiddleware
from pyagent_providers import AnthropicLLM, OpenAILLM

# ── LLMs ──────────────────────────────────────────────────────────────────────
fast_llm      = OpenAILLM("gpt-4o-mini")
smart_llm     = AnthropicLLM("claude-sonnet-4-20250514")
security_llm  = OpenAILLM("gpt-4o")

model_registry = {
    "gpt-4o-mini":              fast_llm,
    "gpt-4o":                   security_llm,
    "claude-sonnet-4-20250514": smart_llm,
}
router = RouterMiddleware(model_registry=model_registry)

# ── Guardrails ─────────────────────────────────────────────────────────────────
input_guard = GuardrailChain([
    LengthGuard(max_chars=50_000, truncate=False),   # hard reject huge pastes
    PIIGuard(redact=True),                            # redact emails/tokens in comments
    ContentGuard(deny_patterns=[                      # block embedded secrets
        __import__("re").compile(r"sk-[A-Za-z0-9]{20,}"),
        __import__("re").compile(r"ghp_[A-Za-z0-9]{36}"),
    ]),
])

# ── Stage 1: iterative code review via cross-reflection ───────────────────────
code_review = CrossReflection(
    generator=router.wrap(
        Agent("author", smart_llm,
              system_prompt=(
                  "You are a senior Python engineer. Review and improve the submitted code. "
                  "Focus on: correctness, edge cases, type hints, docstrings, and performance."
              )),
    ),
    reviewer=router.wrap(
        Agent("critic", smart_llm,
              system_prompt=(
                  "You are a principal engineer doing code review. "
                  "Point out specific issues with line references. "
                  "Reply APPROVED when the code meets production standards."
              )),
    ),
    max_rounds=3,
)

# ── Stage 2: security scan ────────────────────────────────────────────────────
security_pipeline = Pipeline(stages=[
    Agent("security", security_llm,
          system_prompt=(
              "You are a security engineer. Scan the code for: SQL injection, "
              "XSS, insecure deserialization, hardcoded secrets, path traversal, "
              "and OWASP Top 10 issues. Score security 1-10. List every finding."
          )),
])

# ── Stage 3: human escalation for low security scores ────────────────────────
def needs_human_review(result) -> bool:
    """Escalate to human if security score < 8."""
    import re
    match = re.search(r"[Ss]core[:\s]+(\d+)", result.output)
    if match:
        return int(match.group(1)) >= 8
    return True   # pass if no score found

human_escalation = HumanInTheLoop(
    agent=Agent("prep", fast_llm,
                system_prompt="Summarize the security issues for the human reviewer."),
    review_fn=lambda output, meta: _queue_human_review(output),
    high_risk_keywords=["critical", "injection", "hardcoded"],
)

full_pipeline = CompositePattern(
    patterns=[security_pipeline, human_escalation],
    quality_check=needs_human_review,
)

# ── Main review function ───────────────────────────────────────────────────────
async def review_code(code: str) -> dict:
    # 1. Guardrail check
    check = input_guard.check(code)
    if not check.passed:
        return {"error": check.message, "blocked": True}
    safe_code = check.sanitized_content or code

    # 2. Iterative code review
    review_result = await code_review.run(
        f"Review and improve this code:\n\n```python\n{safe_code}\n```"
    )

    # 3. Security scan + optional human escalation
    security_result = await full_pipeline.run(
        f"Security scan:\n\n```python\n{review_result.output}\n```"
    )

    return {
        "improved_code": review_result.output,
        "security_report": security_result.output,
        "review_rounds": review_result.metadata.get("rounds", 0),
        "escalated_to_human": security_result.metadata.get("escalation_level", 0) > 0,
    }


def _queue_human_review(summary: str):
    """Post security findings to the review queue and return a holding decision."""
    import httpx, os
    r = httpx.post(
        os.environ["REVIEW_QUEUE_URL"] + "/reviews",
        json={"summary": summary[:500], "priority": "high", "source": "code-review-agent"},
        headers={"Authorization": f"Bearer {os.environ['REVIEW_QUEUE_TOKEN']}"},
        timeout=15.0,
    )
    r.raise_for_status()
    ticket_id = r.json()["ticket_id"]
    print(f"[SECURITY REVIEW] ticket={ticket_id}")
    from pyagent_patterns.advanced.human_in_the_loop import HumanDecision
    return HumanDecision(approved=True, modified_output=f"[Ticket {ticket_id}]\n{summary}")


# ── Run it ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    code = '''
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)
    '''

    result = asyncio.run(review_code(code))
    print("=== Improved Code ===")
    print(result["improved_code"])
    print("\n=== Security Report ===")
    print(result["security_report"])
    print(f"\nReview rounds: {result['review_rounds']}")
    print(f"Escalated to human: {result['escalated_to_human']}")
```

---

## Expected Output

Running the SQL injection example above:

```
=== Improved Code ===
def get_user(user_id: int) -> dict | None:
    """Fetch a user by ID.

    Args:
        user_id: The integer user ID to look up.

    Returns:
        User dict or None if not found.
    """
    query = "SELECT * FROM users WHERE id = ?"
    return db.execute(query, (user_id,))

=== Security Report ===
Security Score: 3/10

CRITICAL — SQL Injection (original code):
  Line 2: String concatenation used in SQL query.
  Fix: Use parameterized queries (? placeholder). Applied in improved code.

MEDIUM — Missing input validation:
  user_id is typed as `int` but callers may pass strings from HTTP params.
  Fix: Add isinstance(user_id, int) or use a Pydantic model at the boundary.

Review rounds: 2
Escalated to human: True   ← score was 3, below threshold of 8
```

---

## Customization

### Change the review focus

```python
# Security-focused review
Agent("author", smart_llm,
      system_prompt="Review for security vulnerabilities only. OWASP Top 10.")

# Performance-focused review
Agent("author", smart_llm,
      system_prompt="Review for performance. Focus on O(n) complexity, DB queries, caching.")

# Style-focused review
Agent("author", smart_llm,
      system_prompt="Review for PEP 8, type hints, and Google docstring format.")
```

### Adjust escalation threshold

```python
# Always pass to human (security-critical systems)
def always_human(result) -> bool:
    return False   # never passes quality check → always escalates

# Only escalate on critical findings
def only_critical(result) -> bool:
    return "CRITICAL" not in result.output.upper()
```

### Add language support

```python
# Detect language and route to the right specialist
def language_aware_prompt(code: str) -> str:
    if "def " in code or "import " in code:
        return f"Review this Python code:\n\n```python\n{code}\n```"
    elif "function " in code or "const " in code:
        return f"Review this JavaScript/TypeScript code:\n\n```js\n{code}\n```"
    return f"Review this code:\n\n```\n{code}\n```"
```

---

## Cost Profile

| Code snippet | Review rounds | Models used | Approx cost |
|-------------|--------------|-------------|-------------|
| 50-line function | 1–2 | gpt-4o-mini × 2 | $0.001 |
| 200-line class | 2–3 | claude-sonnet × 3 | $0.008 |
| 500-line module | 3 + security | claude-sonnet + gpt-4o | $0.025 |
| Human escalation | — | + human time | $0.002 + human |

---

## See Also

- [CrossReflection pattern](../../packages/patterns/resolution/cross-reflection.md)
- [Guardrails Guide](../../guides/guardrails.md)
- [Routing Guide](../../guides/router.md)
- [HumanInTheLoop pattern](../../packages/patterns/advanced/human-in-the-loop.md)
