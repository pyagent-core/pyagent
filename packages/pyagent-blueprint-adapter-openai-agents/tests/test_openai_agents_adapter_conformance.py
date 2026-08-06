"""Conformance tests for OpenAIAgentsAdapter.

Subclasses the shared `AdapterConformanceSuite` — passing this file is
the acceptance bar for this adapter.
"""

from __future__ import annotations

import pytest
from pyagent_blueprint.conformance import AdapterConformanceSuite
from pyagent_blueprint_adapter_openai_agents.adapter import OpenAIAgentsAdapter


class TestOpenAIAgentsAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> OpenAIAgentsAdapter:
        return OpenAIAgentsAdapter()
