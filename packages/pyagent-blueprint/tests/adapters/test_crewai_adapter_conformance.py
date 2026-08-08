"""Conformance tests for CrewAIAdapter.

Subclasses the shared `AdapterConformanceSuite` — passing this file is
the acceptance bar for this adapter.
"""

from __future__ import annotations

import os

import pytest

# Disable CrewAI's interactive telemetry/tracing prompt in CI/test runs.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from pyagent_blueprint.adapters.integrations.crewai import CrewAIAdapter
from pyagent_blueprint.conformance import AdapterConformanceSuite


class TestCrewAIAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> CrewAIAdapter:
        return CrewAIAdapter()
