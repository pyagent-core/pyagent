"""Guardrail Layer: validate input, output, and inter-agent messages.

Based on: Microsoft Azure AI Agent Patterns Guide
          Augment 2026 "Guardrail Layering (P11)"

Four insertion points:
1. Input guardrail: before the pattern receives user input
2. Inter-agent guardrail: between agent communications
3. Tool-call guardrail: before tool execution
4. Output guardrail: before returning final result
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""

    passed: bool
    message: str = ""
    sanitized_content: str | None = None  # Modified content if sanitization applied


class Guardrail(ABC):
    """Abstract base for all guardrails."""

    @abstractmethod
    def check(self, content: str) -> GuardrailResult:
        """Check content against this guardrail's rules."""
        ...


class LengthGuard(Guardrail):
    """Reject messages exceeding a maximum length.

    Args:
        max_chars: Maximum allowed characters.
        truncate: If True, truncate instead of rejecting.
    """

    def __init__(self, max_chars: int = 10000, truncate: bool = False) -> None:
        self._max_chars = max_chars
        self._truncate = truncate

    def check(self, content: str) -> GuardrailResult:
        if len(content) <= self._max_chars:
            return GuardrailResult(passed=True)
        if self._truncate:
            return GuardrailResult(
                passed=True,
                message=f"Truncated from {len(content)} to {self._max_chars} chars",
                sanitized_content=content[: self._max_chars] + "... [truncated]",
            )
        return GuardrailResult(
            passed=False,
            message=f"Content exceeds maximum length: {len(content)}/{self._max_chars} chars",
        )


class PIIGuard(Guardrail):
    """Detect and optionally redact personally identifiable information.

    Detects: email addresses, phone numbers, SSNs, credit card numbers.

    Args:
        redact: If True, redact PII and pass. If False, reject on detection.
    """

    _PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "ssn": r"\b\d{3}[-]?\d{2}[-]?\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    }

    def __init__(self, redact: bool = True) -> None:
        self._redact = redact

    def check(self, content: str) -> GuardrailResult:
        detections: list[str] = []
        sanitized = content

        for pii_type, pattern in self._PATTERNS.items():
            matches = re.findall(pattern, content)
            if matches:
                detections.append(f"{pii_type}: {len(matches)} found")
                if self._redact:
                    sanitized = re.sub(pattern, f"[REDACTED-{pii_type.upper()}]", sanitized)

        if not detections:
            return GuardrailResult(passed=True)

        if self._redact:
            return GuardrailResult(
                passed=True,
                message=f"PII redacted: {', '.join(detections)}",
                sanitized_content=sanitized,
            )

        return GuardrailResult(
            passed=False,
            message=f"PII detected: {', '.join(detections)}",
        )


class ContentGuard(Guardrail):
    """Block content matching configurable deny patterns.

    Args:
        deny_patterns: List of regex patterns that should be blocked.
        deny_words: List of exact words/phrases to block.
    """

    def __init__(
        self,
        deny_patterns: list[str] | None = None,
        deny_words: list[str] | None = None,
    ) -> None:
        self._patterns = [re.compile(p, re.IGNORECASE) for p in (deny_patterns or [])]
        self._words = [w.lower() for w in (deny_words or [])]

    def check(self, content: str) -> GuardrailResult:
        content_lower = content.lower()

        for word in self._words:
            if word in content_lower:
                return GuardrailResult(passed=False, message=f"Blocked word detected: '{word}'")

        for pattern in self._patterns:
            if pattern.search(content):
                return GuardrailResult(
                    passed=False, message=f"Blocked pattern matched: {pattern.pattern}"
                )

        return GuardrailResult(passed=True)


class GuardrailChain:
    """Chain multiple guardrails together. All must pass.

    Args:
        guardrails: List of guardrails to apply in order.
    """

    def __init__(self, guardrails: list[Guardrail]) -> None:
        self._guardrails = guardrails

    def check(self, content: str) -> GuardrailResult:
        current_content = content

        for guard in self._guardrails:
            result = guard.check(current_content)
            if not result.passed:
                return result
            if result.sanitized_content is not None:
                current_content = result.sanitized_content

        if current_content != content:
            return GuardrailResult(passed=True, sanitized_content=current_content)
        return GuardrailResult(passed=True)
