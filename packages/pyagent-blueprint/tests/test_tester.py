"""Tests for BlueprintTester: contract pass/fail with MockLLM."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyagent_blueprint.loader import load_blueprint
from pyagent_blueprint.tester import BlueprintTester


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_contract_passes() -> None:
    spec = load_blueprint(FIXTURES / "customer_support.yaml")
    tester = BlueprintTester()
    results = await tester.test(spec)
    assert len(results) == 1
    # With MockLLM the workflow should produce output
    assert results[0].output


@pytest.mark.asyncio
async def test_contract_nonexistent_workflow() -> None:
    from pyagent_blueprint.schema import (
        AgentSpec,
        BlueprintSpec,
        ContractSpec,
        MetadataSpec,
        WorkflowSpec,
    )

    spec = BlueprintSpec(
        metadata=MetadataSpec(name="test"),
        agents={"a": AgentSpec(prompt="x")},
        workflows={"w": WorkflowSpec(pattern="pipeline", agents={"a": "a"})},
        contracts={"nonexistent": ContractSpec()},
    )
    tester = BlueprintTester()
    results = await tester.test(spec)
    assert len(results) == 1
    assert not results[0].passed
    assert "non-existent" in (results[0].error or "")


def test_summary_format() -> None:
    from pyagent_blueprint.tester import TestResult

    tester = BlueprintTester()
    results = [
        TestResult(workflow="w1", passed=True, output="ok", checks={"output_non_empty": True}),
        TestResult(workflow="w2", passed=False, error="timeout"),
    ]
    summary = tester.summary(results)
    assert "1/2 passed" in summary
    assert "PASS" in summary
    assert "FAIL" in summary
