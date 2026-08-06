"""Conformance tests for LangGraphAdapter.

Subclasses the shared `AdapterConformanceSuite` published by
`pyagent_blueprint.conformance` — passing this file is the acceptance bar
for this adapter, exactly as it would be for any third-party author.
"""

from __future__ import annotations

import pytest

from pyagent_blueprint.conformance import AdapterConformanceSuite
from pyagent_blueprint_adapter_langgraph.adapter import LangGraphAdapter


class TestLangGraphAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> LangGraphAdapter:
        return LangGraphAdapter()
