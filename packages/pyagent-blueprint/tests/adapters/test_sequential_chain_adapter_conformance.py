"""Run the AdapterConformanceSuite against SequentialChainAdapter."""

from __future__ import annotations

import pytest

from pyagent_blueprint.adapters.reference.sequential_chain import SequentialChainAdapter
from pyagent_blueprint.conformance import AdapterConformanceSuite


class TestSequentialChainAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> SequentialChainAdapter:
        return SequentialChainAdapter()
