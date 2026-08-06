"""Regression test: AdapterRegistry.discover() must not let one
adapter's missing dependency break discovery of every other adapter.

This is what actually makes the "zero mandatory runtime dependency"
claim hold in practice — without this, installing pyagent-blueprint
without the [pyagent] extra would make even the four zero-dependency
reference adapters undiscoverable, because `entry_points().load()`
raises ImportError as soon as it hits the `pyagent` entry point's
`pyagent_patterns` import.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pyagent_blueprint.adapter import AdapterRegistry
from pyagent_blueprint.adapters.reference.single_agent import SingleAgentAdapter


def test_discover_skips_entry_point_with_missing_dependency() -> None:
    broken_ep = MagicMock()
    broken_ep.name = "broken_adapter"
    broken_ep.load.side_effect = ImportError("No module named 'some_missing_framework'")

    working_ep = MagicMock()
    working_ep.name = "single_agent"
    working_ep.load.return_value = SingleAgentAdapter

    with (
        patch(
            "pyagent_blueprint.adapter.entry_points",
            return_value=[broken_ep, working_ep],
            create=True,
        ),
        patch("importlib.metadata.entry_points", return_value=[broken_ep, working_ep]),
    ):
        found = AdapterRegistry.discover()

    assert "broken_adapter" not in found
    assert found.get("single_agent") is SingleAgentAdapter
