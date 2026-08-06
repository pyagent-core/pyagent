"""Conformance tests for SemanticKernelAdapter.

Subclasses the shared `AdapterConformanceSuite` — passing this file is
the acceptance bar for this adapter.
"""

from __future__ import annotations

import pytest
from pyagent_blueprint.conformance import AdapterConformanceSuite
from pyagent_blueprint_adapter_semantic_kernel.adapter import SemanticKernelAdapter


class TestSemanticKernelAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> SemanticKernelAdapter:
        return SemanticKernelAdapter()
