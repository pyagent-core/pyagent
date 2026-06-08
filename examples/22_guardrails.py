"""Example: Guardrails — validate and sanitize agent I/O."""

from pyagent_patterns.guardrails import ContentGuard, GuardrailChain, LengthGuard, PIIGuard


def main():
    chain = GuardrailChain(
        [
            LengthGuard(max_chars=5000, truncate=True),
            PIIGuard(redact=True),
            ContentGuard(deny_words=["password", "secret_key"]),
        ]
    )

    # Test 1: PII redaction
    result = chain.check("Contact user@example.com or call 555-123-4567")
    print(f"PII test — Passed: {result.passed}")
    print(f"  Sanitized: {result.sanitized_content}\n")

    # Test 2: Blocked content
    result = chain.check("The password is abc123")
    print(f"Blocked word test — Passed: {result.passed}")
    print(f"  Message: {result.message}\n")

    # Test 3: Clean content
    result = chain.check("This is a normal request about stock analysis")
    print(f"Clean test — Passed: {result.passed}")


if __name__ == "__main__":
    main()
