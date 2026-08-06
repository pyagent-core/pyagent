"""Run the AdapterConformanceSuite against StateMachineAdapter."""

from __future__ import annotations

import pytest
from pyagent_blueprint.adapters.reference.state_machine import StateMachineAdapter
from pyagent_blueprint.conformance import AdapterConformanceSuite


class TestStateMachineAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> StateMachineAdapter:
        return StateMachineAdapter()
