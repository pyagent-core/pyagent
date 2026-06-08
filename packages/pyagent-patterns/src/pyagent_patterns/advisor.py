"""PatternAdvisor: recommend the best pattern based on task constraints.

Based on: Augment 2026 "Five Decision Rules" for pattern selection.

Decision factors:
1. Task complexity (simple vs multi-step vs adversarial)
2. Quality requirement (draft vs production)
3. Budget constraint (tokens/$)
4. Latency requirement (real-time vs batch)
5. Reliability requirement (best-effort vs fault-tolerant)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Quality(StrEnum):
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class Latency(StrEnum):
    REALTIME = "realtime"  # < 2s
    INTERACTIVE = "interactive"  # < 10s
    BATCH = "batch"  # minutes OK


@dataclass
class Constraints:
    """Task constraints for pattern selection."""

    quality: Quality = Quality.STANDARD
    latency: Latency = Latency.INTERACTIVE
    max_cost_usd: float = 0.05
    fault_tolerant: bool = False
    multi_step: bool = False


@dataclass
class Recommendation:
    """A pattern recommendation with reasoning."""

    pattern: str
    reason: str
    estimated_calls: int
    estimated_cost_range: str
    alternatives: list[str]


class PatternAdvisor:
    """Recommend patterns based on task description and constraints.

    Usage:
        advisor = PatternAdvisor()
        rec = advisor.recommend("Write and review code", Constraints(quality=Quality.HIGH))
        print(rec.pattern, rec.reason)
    """

    def recommend(self, task: str, constraints: Constraints | None = None) -> Recommendation:
        """Recommend the best pattern for the given task and constraints."""
        c = constraints or Constraints()
        task_lower = task.lower()

        # Decision tree based on Augment 2026 "Five Decision Rules"

        # Rule 1: Simple single-step tasks → Pipeline or single agent
        if (
            not c.multi_step
            and c.quality in (Quality.DRAFT, Quality.STANDARD)
            and c.latency == Latency.REALTIME
        ):
            return Recommendation(
                pattern="pipeline",
                reason="Simple task with real-time latency → minimal sequential processing",
                estimated_calls=1,
                estimated_cost_range="$0.001-0.003",
                alternatives=["talker_reasoner"],
            )

        # Rule 2: Cost-sensitive → Route to cheapest viable model
        if c.max_cost_usd < 0.01:
            return Recommendation(
                pattern="talker_reasoner",
                reason="Tight budget → use cheap model for easy, expensive only when needed",
                estimated_calls=1,
                estimated_cost_range="$0.001-0.005",
                alternatives=["pipeline"],
            )

        # Rule 3: High reliability / fault tolerance → Voting or Fan-Out
        if c.fault_tolerant:
            return Recommendation(
                pattern="voting",
                reason="Fault-tolerant requirement → multiple independent agents with consensus",
                estimated_calls=3,
                estimated_cost_range="$0.006-0.012",
                alternatives=["fan_out_fan_in"],
            )

        # Rule 4: High quality → Reflection, Debate, or Evaluator
        if c.quality in (Quality.HIGH, Quality.CRITICAL):
            # Check for adversarial/debate keywords
            if any(
                w in task_lower for w in ["compare", "pros and cons", "debate", "argue", "versus"]
            ):
                return Recommendation(
                    pattern="debate",
                    reason="High quality + adversarial task → structured debate with judge",
                    estimated_calls=7,
                    estimated_cost_range="$0.014-0.028",
                    alternatives=["evaluator_optimizer", "cross_reflection"],
                )

            # Check for code/writing that benefits from review
            if any(w in task_lower for w in ["write", "code", "generate", "create", "draft"]):
                return Recommendation(
                    pattern="self_reflection",
                    reason="High quality creative/code task → generate-critique-refine loop",
                    estimated_calls=4,
                    estimated_cost_range="$0.004-0.012",
                    alternatives=["cross_reflection", "evaluator_optimizer"],
                )

            return Recommendation(
                pattern="evaluator_optimizer",
                reason="High quality task → explicit evaluation criteria with optimization",
                estimated_calls=4,
                estimated_cost_range="$0.004-0.008",
                alternatives=["self_reflection"],
            )

        # Rule 5: Multi-step/complex → Supervisor, Hierarchical, or Pipeline
        if c.multi_step or any(
            w in task_lower for w in ["steps", "process", "workflow", "pipeline"]
        ):
            if any(w in task_lower for w in ["team", "delegate", "manage", "coordinate"]):
                return Recommendation(
                    pattern="hierarchical",
                    reason="Multi-step with team coordination → hierarchical delegation",
                    estimated_calls=7,
                    estimated_cost_range="$0.010-0.020",
                    alternatives=["supervisor", "orchestrator_workers"],
                )

            if any(w in task_lower for w in ["classify", "route", "triage", "categorize"]):
                return Recommendation(
                    pattern="supervisor",
                    reason="Multi-step with classification → supervisor routes to specialists",
                    estimated_calls=3,
                    estimated_cost_range="$0.004-0.008",
                    alternatives=["pipeline"],
                )

            return Recommendation(
                pattern="pipeline",
                reason="Multi-step sequential task → stage-by-stage processing",
                estimated_calls=4,
                estimated_cost_range="$0.004-0.008",
                alternatives=["supervisor"],
            )

        # Default: Pipeline (safest general-purpose)
        return Recommendation(
            pattern="pipeline",
            reason="General-purpose task → sequential pipeline with composable stages",
            estimated_calls=2,
            estimated_cost_range="$0.002-0.004",
            alternatives=["supervisor", "self_reflection"],
        )
