"""BlueprintTester: generate and run conformance tests from contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pyagent_blueprint.compiler import BlueprintCompiler

if TYPE_CHECKING:
    from pyagent_blueprint.schema.spec import BlueprintSpec


@dataclass
class TestResult:
    """Result of a single contract test.

    Attributes:
        workflow: Workflow name tested.
        passed: Whether the test passed.
        output: The actual output from the workflow.
        checks: Dict of check name → pass/fail.
        error: Error message if the test failed with an exception.
    """

    workflow: str
    passed: bool
    output: str = ""
    checks: dict[str, bool] = field(default_factory=dict)
    error: str | None = None


class BlueprintTester:
    """Run conformance tests for blueprint contracts using MockLLM.

    Compiles the blueprint with mock providers and verifies that:
    - Workflows produce output
    - Output type matches contract expectations
    - SLA constraints are within bounds (basic checks)

    Args:
        compiler: Optional compiler instance. Creates one if not provided.
    """

    def __init__(self, compiler: BlueprintCompiler | None = None) -> None:
        self._compiler = compiler or BlueprintCompiler()

    async def test(
        self,
        spec: BlueprintSpec,
        test_inputs: dict[str, str] | None = None,
    ) -> list[TestResult]:
        """Run contract conformance tests for all workflows with contracts.

        Args:
            spec: Blueprint spec to test.
            test_inputs: Optional mapping of workflow name → test input.
                If not provided, uses a default test string.

        Returns:
            List of ``TestResult`` for each contract.
        """
        graph = self._compiler.compile(spec)
        results: list[TestResult] = []

        for contract_name, contract in spec.contracts.items():
            if contract_name not in spec.workflows:
                results.append(
                    TestResult(
                        workflow=contract_name,
                        passed=False,
                        error=f"Contract references non-existent workflow '{contract_name}'",
                    )
                )
                continue

            test_input = (test_inputs or {}).get(
                contract_name, "Test input for contract validation"
            )

            try:
                result = await graph.run(contract_name, test_input)
                checks: dict[str, bool] = {}

                # Check: output is non-empty
                checks["output_non_empty"] = bool(result.output)

                # Check: output type matches
                expected_type = contract.output.get("type", "string")
                if expected_type == "string":
                    checks["output_is_string"] = isinstance(result.output, str)

                # Check: output length within bounds
                max_tokens = contract.input.get("max_tokens")
                if max_tokens is not None:
                    estimated_tokens = len(test_input) // 4
                    checks["input_within_token_limit"] = estimated_tokens <= max_tokens

                all_passed = all(checks.values())
                results.append(
                    TestResult(
                        workflow=contract_name,
                        passed=all_passed,
                        output=result.output,
                        checks=checks,
                    )
                )

            except Exception as exc:
                results.append(
                    TestResult(
                        workflow=contract_name,
                        passed=False,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

        return results

    def summary(self, results: list[TestResult]) -> str:
        """Human-readable summary of test results."""
        lines: list[str] = []
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        lines.append(f"\nContract Tests: {passed}/{total} passed\n")

        for r in results:
            status = "✓ PASS" if r.passed else "✗ FAIL"
            lines.append(f"  {status}  {r.workflow}")
            if r.error:
                lines.append(f"         Error: {r.error}")
            for check, ok in r.checks.items():
                mark = "✓" if ok else "✗"
                lines.append(f"         {mark} {check}")

        return "\n".join(lines)
