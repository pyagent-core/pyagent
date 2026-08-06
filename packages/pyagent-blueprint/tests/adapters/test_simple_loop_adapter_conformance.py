"""Run the AdapterConformanceSuite against SimpleLoopAdapter."""

from __future__ import annotations

import pytest

from pyagent_blueprint.adapters.reference.simple_loop import SimpleLoopAdapter
from pyagent_blueprint.conformance import AdapterConformanceSuite


class TestSimpleLoopAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> SimpleLoopAdapter:
        return SimpleLoopAdapter()
