"""Run the AdapterConformanceSuite against our own PyAgentAdapter.

This is the first real signal on whether the RuntimeAdapter contract
holds up (TRANSFORMATION-PLAN.md Step 3 / mega plan Phase 2).
"""

from __future__ import annotations

import pytest
from pyagent_blueprint.adapters.pyagent_adapter import PyAgentAdapter
from pyagent_blueprint.conformance import AdapterConformanceSuite


class TestPyAgentAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> PyAgentAdapter:
        return PyAgentAdapter()
