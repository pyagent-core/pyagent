"""Run the AdapterConformanceSuite against SingleAgentAdapter."""

from __future__ import annotations

import pytest

from pyagent_blueprint.adapters.reference.single_agent import SingleAgentAdapter
from pyagent_blueprint.conformance import AdapterConformanceSuite


class TestSingleAgentAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> SingleAgentAdapter:
        return SingleAgentAdapter()
