"""ObservabilitySpec: tracing + cost budget + alert thresholds."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TracingConfig(BaseModel):
    """Tracing/telemetry configuration."""

    enabled: bool = Field(default=True)
    exporter: str = Field(default="console", description="console | otlp | jaeger")
    endpoint: str = Field(default="")


class CostBudgetConfig(BaseModel):
    """Cost budget and alerting."""

    daily_usd: float = Field(default=100.0, gt=0)
    alert_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class ObservabilitySpec(BaseModel):
    """Observability configuration for a blueprint."""

    tracing: TracingConfig = Field(default_factory=TracingConfig)
    cost_budget: CostBudgetConfig | None = Field(default=None)
