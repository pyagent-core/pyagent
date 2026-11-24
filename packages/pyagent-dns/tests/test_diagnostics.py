"""Tests for the dns diagnostic codes and their bridge to pyagent-blueprint's CompileDiagnostic."""

from __future__ import annotations

import pytest
from pyagent_dns.diagnostics import (
    ALL_CODES,
    AUTHORITY_UNSUPPORTED,
    DNS_UNSUPPORTED,
    code_for,
    to_compile_diagnostic,
)


def test_both_codes_are_defined_once_as_warnings_with_a_proposed_gap() -> None:
    assert [c.code for c in ALL_CODES] == [DNS_UNSUPPORTED, AUTHORITY_UNSUPPORTED]
    for code in ALL_CODES:
        assert code.severity == "warning"
        assert code.gap == "G11 (proposed)"
        assert code.description


@pytest.mark.parametrize("name", [DNS_UNSUPPORTED, AUTHORITY_UNSUPPORTED])
def test_code_for_returns_the_code_with_that_name(name: str) -> None:
    assert code_for(name).code == name


def test_an_unknown_code_name_is_a_key_error_that_names_it() -> None:
    with pytest.raises(KeyError, match="NOT_A_CODE"):
        code_for("NOT_A_CODE")


@pytest.mark.parametrize("by", ["name", "object"])
def test_a_compile_diagnostic_is_built_with_a_real_blueprint_code(by: str) -> None:
    pytest.importorskip("pyagent_blueprint")
    from pyagent_blueprint.adapter import CompileDiagnostic
    from pyagent_blueprint.diagnostics import DiagnosticSeverity

    code = DNS_UNSUPPORTED if by == "name" else code_for(DNS_UNSUPPORTED)
    diagnostic = to_compile_diagnostic(code, "x-pyagent:dns", "adapter cannot resolve names")

    assert isinstance(diagnostic, CompileDiagnostic)
    assert diagnostic.code.code == DNS_UNSUPPORTED
    assert diagnostic.code.severity is DiagnosticSeverity.WARNING
    assert diagnostic.code.gap == "G11 (proposed)"
    assert diagnostic.path == "x-pyagent:dns"
    assert diagnostic.detail == "adapter cannot resolve names"


def test_the_detail_defaults_to_the_codes_description() -> None:
    pytest.importorskip("pyagent_blueprint")
    diagnostic = to_compile_diagnostic(AUTHORITY_UNSUPPORTED, "x-pyagent:dns")
    assert diagnostic.detail == code_for(AUTHORITY_UNSUPPORTED).description


def test_an_unknown_code_name_is_rejected_before_anything_is_built() -> None:
    pytest.importorskip("pyagent_blueprint")
    with pytest.raises(KeyError):
        to_compile_diagnostic("NOPE", "x-pyagent:dns")
