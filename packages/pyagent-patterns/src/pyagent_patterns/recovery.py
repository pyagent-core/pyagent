"""Error Recovery: BoundedExecution and CircuitBreaker for multi-agent patterns.

BoundedExecution: wrap any pattern with max iterations, token, and timeout limits.
CircuitBreaker: stop cascading failures with failure threshold + reset timeout.

Based on: arxiv:2604.11378 "three-level recovery protocol"
          Augment 2026 "Bounded Execution" emergent pattern
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import StrEnum

from pyagent_patterns.base import Context, Pattern, Result


class CircuitState(StrEnum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class BoundedExecution:
    """Wrap a pattern with resource limits.

    Three-level recovery:
    1. Retry with same pattern
    2. Fallback to a cheaper/simpler pattern
    3. Graceful degradation (return partial result)

    Args:
        pattern: The primary pattern to execute.
        fallback: Optional simpler pattern to use on failure.
        max_retries: Maximum retry attempts before escalating.
        timeout_seconds: Maximum wall-clock time for the entire execution.
        max_tokens: Maximum total tokens before stopping.
    """

    pattern: Pattern
    fallback: Pattern | None = None
    max_retries: int = 2
    timeout_seconds: float = 300.0
    max_tokens: int = 100_000

    async def run(self, task: str, context: Context | None = None) -> Result:
        """Execute with bounded resources and three-level recovery."""
        start = time.perf_counter()

        # Level 1: Try primary pattern with retries
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            elapsed = time.perf_counter() - start
            if elapsed > self.timeout_seconds:
                break

            try:
                remaining = self.timeout_seconds - elapsed
                result = await asyncio.wait_for(
                    self.pattern.run(task, context),
                    timeout=remaining,
                )
                if result.token_estimate <= self.max_tokens:
                    result.metadata["recovery_level"] = 0
                    result.metadata["attempts"] = attempt
                    return result
                # Token limit exceeded — try next level
                last_error = Exception(f"Token limit exceeded: {result.token_estimate}/{self.max_tokens}")
                break
            except TimeoutError:
                last_error = TimeoutError(f"Timeout after {self.timeout_seconds}s")
                break
            except Exception as e:
                last_error = e
                continue

        # Level 2: Fallback pattern
        if self.fallback:
            try:
                remaining = max(0.0, self.timeout_seconds - (time.perf_counter() - start))
                result = await asyncio.wait_for(
                    self.fallback.run(task, context),
                    timeout=remaining if remaining > 0 else 30.0,
                )
                result.metadata["recovery_level"] = 1
                result.metadata["fallback_reason"] = str(last_error)
                return result
            except Exception:
                pass

        # Level 3: Graceful degradation
        return Result(
            output=f"[Degraded] Unable to complete task after {self.max_retries} attempts. Last error: {last_error}",
            metadata={
                "recovery_level": 2,
                "degraded": True,
                "last_error": str(last_error),
            },
        )


class CircuitBreaker:
    """Prevent cascading failures in multi-agent systems.

    When a pattern fails repeatedly, the circuit opens and rejects
    requests immediately. After a reset timeout, it enters half-open
    state and allows one test request through.

    Args:
        failure_threshold: Number of consecutive failures before opening.
        reset_timeout_seconds: Seconds before transitioning from open to half-open.
        fallback_result: Result to return when circuit is open.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_seconds: float = 60.0,
        fallback_result: str = "[Circuit Open] Service temporarily unavailable.",
    ) -> None:
        self._threshold = failure_threshold
        self._reset_timeout = reset_timeout_seconds
        self._fallback_result = fallback_result
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and time.time() - self._last_failure_time > self._reset_timeout:
            self._state = CircuitState.HALF_OPEN
        return self._state

    async def execute(self, pattern: Pattern, task: str, context: Context | None = None) -> Result:
        """Execute a pattern through the circuit breaker."""
        current_state = self.state

        if current_state == CircuitState.OPEN:
            return Result(
                output=self._fallback_result,
                metadata={"circuit_state": "open", "failure_count": self._failure_count},
            )

        try:
            result = await pattern.run(task, context)
            self._on_success()
            result.metadata["circuit_state"] = self._state.value
            return result
        except Exception as e:
            self._on_failure()
            if self._state == CircuitState.OPEN:
                return Result(
                    output=self._fallback_result,
                    metadata={
                        "circuit_state": "open",
                        "failure_count": self._failure_count,
                        "last_error": str(e),
                    },
                )
            raise

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._threshold:
            self._state = CircuitState.OPEN
