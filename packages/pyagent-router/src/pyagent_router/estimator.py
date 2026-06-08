"""CostEstimator: estimate LLM call cost based on token count and model pricing.

Maintains a registry of model pricing (per 1M input/output tokens)
and estimates cost for a given task and model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """Pricing for a model per 1M tokens."""

    input_per_million: float
    output_per_million: float


@dataclass(frozen=True)
class CostEstimate:
    """Estimated cost for a single LLM call.

    Attributes:
        model: Model name.
        input_tokens: Estimated input tokens.
        output_tokens: Estimated output tokens.
        input_cost: Cost for input tokens in USD.
        output_cost: Cost for output tokens in USD.
        total_cost: Total estimated cost in USD.
    """

    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost


# Pricing as of mid-2025 (per 1M tokens)
DEFAULT_PRICING: dict[str, ModelPricing] = {
    "gpt-4o": ModelPricing(2.50, 10.00),
    "gpt-4o-mini": ModelPricing(0.15, 0.60),
    "gpt-4.1": ModelPricing(2.00, 8.00),
    "gpt-4.1-mini": ModelPricing(0.40, 1.60),
    "gpt-4.1-nano": ModelPricing(0.10, 0.40),
    "o3": ModelPricing(10.00, 40.00),
    "o3-mini": ModelPricing(1.10, 4.40),
    "o4-mini": ModelPricing(1.10, 4.40),
    "claude-sonnet-4": ModelPricing(3.00, 15.00),
    "claude-haiku-3.5": ModelPricing(0.80, 4.00),
    "gemini-2.5-flash": ModelPricing(0.15, 0.60),
    "gemini-2.5-pro": ModelPricing(1.25, 10.00),
}


class CostEstimator:
    """Estimate LLM call costs based on model pricing registry.

    Args:
        pricing: Optional custom pricing dict. Defaults to built-in pricing table.
        default_output_ratio: Estimated output/input token ratio when output length unknown.
    """

    def __init__(
        self,
        pricing: dict[str, ModelPricing] | None = None,
        default_output_ratio: float = 0.5,
    ) -> None:
        self._pricing = pricing or dict(DEFAULT_PRICING)
        self._output_ratio = default_output_ratio

    def estimate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int | None = None,
    ) -> CostEstimate:
        """Estimate cost for a single LLM call.

        Args:
            model: Model name (must be in pricing registry).
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens. If None, estimated from input.

        Returns:
            CostEstimate with breakdown.

        Raises:
            KeyError: If model not found in pricing registry.
        """
        if model not in self._pricing:
            raise KeyError(
                f"Model '{model}' not in pricing registry. "
                f"Available: {', '.join(sorted(self._pricing.keys()))}"
            )

        pricing = self._pricing[model]
        est_output = output_tokens if output_tokens is not None else int(input_tokens * self._output_ratio)

        return CostEstimate(
            model=model,
            input_tokens=input_tokens,
            output_tokens=est_output,
            input_cost=input_tokens * pricing.input_per_million / 1_000_000,
            output_cost=est_output * pricing.output_per_million / 1_000_000,
        )

    def estimate_from_text(self, model: str, text: str) -> CostEstimate:
        """Estimate cost from raw text (approximates 4 chars per token)."""
        input_tokens = len(text) // 4
        return self.estimate(model, input_tokens)

    def compare(self, text: str, models: list[str] | None = None) -> list[CostEstimate]:
        """Compare costs across multiple models for the same input.

        Args:
            text: The input text.
            models: Models to compare. Defaults to all registered models.

        Returns:
            List of CostEstimates sorted by total_cost ascending.
        """
        target_models = models or list(self._pricing.keys())
        estimates = [self.estimate_from_text(m, text) for m in target_models if m in self._pricing]
        return sorted(estimates, key=lambda e: e.total_cost)

    @property
    def available_models(self) -> list[str]:
        return sorted(self._pricing.keys())
