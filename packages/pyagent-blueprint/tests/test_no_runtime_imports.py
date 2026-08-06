"""Fails CI if pyagent_blueprint core imports an agent-execution
framework anywhere outside `adapters/`.

This is the enforcement mechanism behind the "core has ZERO dependency
on any agent-execution framework" claim in TRANSFORMATION-PLAN.md
Section 3. Only files under `src/pyagent_blueprint/adapters/` may import
`pyagent_patterns` (or, in future, `langgraph`, `crewai`, `autogen`,
etc.).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).parent.parent / "src" / "pyagent_blueprint"

#: Package/module prefixes considered "runtime" (agent-execution
#: framework) imports. Core (outside adapters/) must never import these.
RUNTIME_IMPORT_PREFIXES = (
    "pyagent_patterns",
    "pyagent_router",
    "pyagent_providers",
    "pyagent_context",
)


def _iter_core_python_files() -> list[Path]:
    files = []
    for path in SRC_ROOT.rglob("*.py"):
        if "adapters" in path.relative_to(SRC_ROOT).parts:
            continue
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def _imported_module_names(tree: ast.Module) -> set[str]:
    """Collect imported module names, excluding anything nested inside an
    `if TYPE_CHECKING:` block — those cost nothing at install/runtime and
    are purely for static type checkers, so they don't violate the
    "zero installable dependency" guarantee this test enforces."""
    names: set[str] = set()

    def _is_type_checking_guard(node: ast.If) -> bool:
        test = node.test
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            return True
        return False

    class _Visitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If) -> None:  # noqa: N802 - ast API
            if _is_type_checking_guard(node):
                return  # skip the guarded body entirely
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:  # noqa: N802 - ast API
            for alias in node.names:
                names.add(alias.name)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802 - ast API
            if node.module:
                names.add(node.module)

    _Visitor().visit(tree)
    return names


@pytest.mark.parametrize("path", _iter_core_python_files(), ids=lambda p: str(p.name))
def test_core_module_has_no_runtime_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(), filename=str(path))
    imported = _imported_module_names(tree)

    offending = [
        name
        for name in imported
        if any(name == prefix or name.startswith(prefix + ".") for prefix in RUNTIME_IMPORT_PREFIXES)
    ]
    assert not offending, (
        f"{path.relative_to(SRC_ROOT.parent.parent)} imports runtime framework module(s) "
        f"{offending} outside adapters/ — move this logic into adapters/ instead."
    )
