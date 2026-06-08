"""ModelSelector: pick the best model based on difficulty, cost, and capability constraints.

Combines DifficultyScorer output with CostEstimator to select the
cheapest model that meets quality requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pyagent_router.estimator import CostEstimate, CostEstimator
from pyagent_router.scorer import DifficultyScore, DifficultyScorer


class Capability(StrEnum):
    """Model capabilities for filtering."""

    CODE = "code"
    MATH = "math"
    REASONING = "reasoning"
    CREATIVE = "creative"
    GENERAL = "general"
    VISION = "vision"


@dataclass
class ModelSpec:
    """Specification of a model's capabilities and constraints.

    Attributes:
        name: Model identifier (must match pricing registry).
        min_difficulty: Minimum difficulty score this model should handle.
        max_difficulty: Maximum difficulty score this model should handle.
        capabilities: Set of capabilities this model excels at.
        max_context: Maximum context window in tokens.
    """

    name: str
    min_difficulty: int = 1
    max_difficulty: int = 10
    capabilities: set[Capability] = field(default_factory=lambda: {Capability.GENERAL})
    max_context: int = 128_000


DEFAULT_MODEL_SPECS: list[ModelSpec] = [
    ModelSpec("gpt-4.1-nano", 1, 3, {Capability.GENERAL}, 1_000_000),
    ModelSpec("gpt-4o-mini", 1, 5, {Capability.GENERAL, Capability.CODE}, 128_000),
    ModelSpec(
        "gpt-4.1-mini", 1, 6, {Capability.GENERAL, Capability.CODE, Capability.REASONING}, 1_000_000
    ),
    ModelSpec(
        "gpt-4o",
        3,
        8,
        {Capability.GENERAL, Capability.CODE, Capability.CREATIVE, Capability.VISION},
        128_000,
    ),
    ModelSpec(
        "gpt-4.1", 4, 9, {Capability.GENERAL, Capability.CODE, Capability.REASONING}, 1_000_000
    ),
    ModelSpec(
        "claude-sonnet-4",
        5,
        10,
        {Capability.GENERAL, Capability.CODE, Capability.REASONING, Capability.CREATIVE},
        200_000,
    ),
    ModelSpec("o3-mini", 6, 10, {Capability.REASONING, Capability.MATH, Capability.CODE}, 200_000),
    ModelSpec("o3", 8, 10, {Capability.REASONING, Capability.MATH, Capability.CODE}, 200_000),
]


@dataclass(frozen=True)
class SelectionResult:
    """Result of model selection.

    Attributes:
        model: Selected model name.
        difficulty: The difficulty assessment.
        cost_estimate: Estimated cost for this model.
        reason: Human-readable explanation of why this model was chosen.
        alternatives: Other models that were considered.
    """

    model: str
    difficulty: DifficultyScore
    cost_estimate: CostEstimate
    reason: str
    alternatives: list[str] = field(default_factory=list)


class ModelSelector:
    """Select the optimal model based on task difficulty and cost.

    Strategy: find the cheapest model whose difficulty range covers the task
    and whose capabilities match the required capability (if specified).

    Args:
        specs: List of ModelSpec definitions. Defaults to built-in specs.
        cost_estimator: CostEstimator instance. Created automatically if None.
        scorer: DifficultyScorer instance. Created automatically if None.
    """

    def __init__(
        self,
        specs: list[ModelSpec] | None = None,
        cost_estimator: CostEstimator | None = None,
        scorer: DifficultyScorer | None = None,
    ) -> None:
        self._specs = specs or list(DEFAULT_MODEL_SPECS)
        self._estimator = cost_estimator or CostEstimator()
        self._scorer = scorer or DifficultyScorer()

    def select(
        self,
        task: str,
        required_capability: Capability | None = None,
    ) -> SelectionResult:
        """Select the best model for a given task.

        Args:
            task: The task text to analyze.
            required_capability: Optional capability filter.

        Returns:
            SelectionResult with chosen model and reasoning.
        """
        difficulty = self._scorer.score(task)

        # Filter specs by difficulty range and capability
        candidates: list[ModelSpec] = []
        for spec in self._specs:
            if spec.min_difficulty <= difficulty.score <= spec.max_difficulty and (
                required_capability is None or required_capability in spec.capabilities
            ):
                candidates.append(spec)

        if not candidates:
            # Fallback to the most capable model
            candidates = [self._specs[-1]]

        # Estimate cost for each candidate and pick cheapest
        scored: list[tuple[ModelSpec, CostEstimate]] = []
        for spec in candidates:
            try:
                estimate = self._estimator.estimate_from_text(spec.name, task)
                scored.append((spec, estimate))
            except KeyError:
                continue

        if not scored:
            # Last resort fallback
            spec = self._specs[0]
            estimate = CostEstimate(spec.name, len(task) // 4, len(task) // 8, 0.0, 0.0)
            scored = [(spec, estimate)]

        scored.sort(key=lambda x: x[1].total_cost)
        chosen_spec, chosen_cost = scored[0]
        alternatives = [s.name for s, _ in scored[1:]]

        reason = (
            f"Difficulty {difficulty.score}/10 ({difficulty.category}) → "
            f"{chosen_spec.name} (cheapest candidate at ${chosen_cost.total_cost:.6f})"
        )

        return SelectionResult(
            model=chosen_spec.name,
            difficulty=difficulty,
            cost_estimate=chosen_cost,
            reason=reason,
            alternatives=alternatives,
        )
