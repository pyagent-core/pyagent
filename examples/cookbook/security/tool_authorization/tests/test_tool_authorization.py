"""Unit and contract tests for the tool authorization recipe."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ..api import authorize_tool_call
from ..models import AuthorizationRequest
from ..pipeline import run_pipeline

if TYPE_CHECKING:
    from pyagent_patterns.base import MockLLM


@pytest.mark.asyncio
async def test_pipeline_denies_vault_and_allows_positions(mock_analyst_llm: MockLLM) -> None:
    """The pipeline must block ungranted vault calls and execute granted position reads."""
    res = await run_pipeline("Audit portfolio ACC-101", llm=mock_analyst_llm)

    assert "Portfolio holds AAPL and MSFT." in res["output"]
    decisions = res["decisions"]
    assert len(decisions) == 2

    # First attempt: client-vault-reader -> DENIED
    assert decisions[0]["capability"] == "client-vault-reader"
    assert decisions[0]["allowed"] is False
    assert decisions[0]["reason_code"] == "NO_GRANT"

    # Second attempt: portfolio-data.reader -> ALLOWED
    assert decisions[1]["capability"] == "portfolio-data.reader"
    assert decisions[1]["allowed"] is True
    assert decisions[1]["reason_code"] == "GRANT_FOUND"


@pytest.mark.asyncio
async def test_api_authorize_allowed_and_denied() -> None:
    """FastAPI endpoint evaluates allow/deny correctly."""
    # Denied call
    req_denied = AuthorizationRequest(
        principal="portfolio_analyst",
        capability="client-vault-reader",
        purpose="portfolio_audit",
        query="ACC-101",
    )
    res_denied = await authorize_tool_call(req_denied)
    assert res_denied.allowed is False
    assert res_denied.reason_code == "NO_GRANT"
    assert res_denied.output is None

    # Allowed call
    req_allowed = AuthorizationRequest(
        principal="portfolio_analyst",
        capability="portfolio-data.reader",
        purpose="portfolio_audit",
        query="ACC-101",
    )
    res_allowed = await authorize_tool_call(req_allowed)
    assert res_allowed.allowed is True
    assert res_allowed.reason_code == "GRANT_FOUND"
    assert "AAPL=150" in (res_allowed.output or "")


@pytest.mark.asyncio
async def test_compliance_export_requires_approval() -> None:
    """Exporting to compliance requires explicit human-in-the-loop approval."""
    # Without approval
    req_no_approval = AuthorizationRequest(
        principal="portfolio_analyst",
        capability="compliance-exporter",
        purpose="portfolio_audit",
        query="ACC-101",
    )
    res_no_approval = await authorize_tool_call(req_no_approval)
    assert res_no_approval.allowed is False
    assert res_no_approval.reason_code == "APPROVAL_REQUIRED"
