"""Tests for trace event payloads. The payload is the audit record, so it is checked field by field."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pyagent_dns.authority import Action, Decision, Outcome, ResourceSelector
from pyagent_dns.events import (
    EVENT_DECISION,
    EVENT_RESOLUTION,
    DnsAttributes,
    build_decision_payload,
    build_resolution_payload,
    decision_event,
    resolution_event,
)
from pyagent_dns.records import RecordStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyagent_dns.registry import NameRegistry
    from pyagent_dns.resolver import Resolver

SRC = Path(__file__).parent.parent / "src"


def test_an_allow_decision_payload_carries_the_evidence_to_explain_it(
    ask: Callable[..., Decision], resolver: Resolver
) -> None:
    decision = ask(records_requested=10)
    resolution = resolver.resolve("portfolio-data.reader")
    assert resolution is not None

    payload = build_decision_payload(decision)

    assert payload["outcome"] == "allow_with_obligations"
    assert payload["reason_code"] == "GRANT_FOUND"
    assert payload["principal"] == "research_agent"
    assert payload["action"] == "call"
    assert payload["capability"] == "portfolio-data.reader"
    assert payload["record_name"] == "portfolio-data.reader"
    assert payload["record_version"] == "3.2.1"
    assert payload["record_fingerprint"] == resolution.fingerprint
    assert payload["verification_status"] == "verified"
    assert payload["grant_path"] == ["g_portfolio"]
    assert payload["policy_versions"] == ["v14"]
    assert payload["data_classes"] == ["internal"]
    assert payload["effective_limits"]["max_records_per_call"] == 500
    assert "log_decision" in payload["obligations"]


def test_a_deny_decision_payload_names_why_and_what_was_resolved(
    ask: Callable[..., Decision],
) -> None:
    payload = build_decision_payload(ask("client-vault-reader"))
    assert payload["outcome"] == "deny"
    assert payload["reason_code"] == "NO_GRANT"
    assert payload["record_name"] == "client-vault-reader"
    assert payload["verification_status"] == "verified"
    assert payload["grant_path"] == []


def test_a_deny_for_an_unknown_name_carries_no_record_evidence_but_still_serializes() -> None:
    decision = Decision(Outcome.DENY, "NO_RECORD", "none", "agent", Action.CALL, "ghost")
    payload = build_decision_payload(decision)
    assert payload["reason_code"] == "NO_RECORD"
    assert payload["record_fingerprint"] is None
    assert payload["verification_status"] is None


def test_the_decision_payload_is_json_serializable(ask: Callable[..., Decision]) -> None:
    """Exporters write payloads out as JSON, so no enum or tuple may leak through."""
    allow = ask(records_requested=1)
    deny = ask("client-vault-reader")
    for decision in (allow, deny):
        assert json.loads(json.dumps(build_decision_payload(decision)))


def test_an_approval_payload_carries_the_binding_hash_and_never_the_request(
    ask: Callable[..., Decision],
) -> None:
    decision = ask(
        action=Action.EXPORT,
        resource=ResourceSelector(("confidential",)),
        request_payload=b"export all client SSNs",
    )
    payload = build_decision_payload(decision)
    assert payload["outcome"] == "require_approval"
    assert payload["approval_binding"].startswith("sha256:")
    assert "SSNs" not in json.dumps(payload)


def test_a_resolution_payload_distinguishes_lifecycle_from_verification(
    resolver: Resolver, registry: NameRegistry
) -> None:
    registry.revoke("portfolio-data.reader")
    resolution = resolver.resolve("portfolio-data.reader")
    assert resolution is not None
    payload = build_resolution_payload(resolution)
    assert payload["record_name"] == "portfolio-data.reader"
    assert payload["record_version"] == "3.2.1"
    assert payload["record_fingerprint"] == resolution.fingerprint
    assert payload["status"] == str(RecordStatus.REVOKED)
    assert payload["verification_status"] == "verified"
    assert payload["verified"] is True
    assert payload["from_cache"] is False
    assert payload["resolved_at"] == resolution.resolved_at
    json.dumps(payload)


def test_every_attribute_key_is_namespaced_and_unique() -> None:
    keys = [v for k, v in vars(DnsAttributes).items() if not k.startswith("_")]
    assert keys
    assert all(key.startswith("pyagent.dns.") for key in keys)
    assert len(set(keys)) == len(keys)


# -- TraceEvent construction -----------------------------------------------------------------


def test_decision_event_is_a_trace_event_carrying_the_decision_payload(
    ask: Callable[..., Decision],
) -> None:
    trace = pytest.importorskip("pyagent_trace.events")
    decision = ask()
    event = decision_event(decision, agent_name="research_agent")
    assert isinstance(event, trace.TraceEvent)
    assert event.event_type == EVENT_DECISION == "authority_decision"
    assert event.agent_name == "research_agent"
    assert event.payload == build_decision_payload(decision)
    assert event.timestamp > 0


def test_resolution_event_is_a_trace_event_carrying_the_resolution_payload(
    resolver: Resolver,
) -> None:
    trace = pytest.importorskip("pyagent_trace.events")
    resolution = resolver.resolve("portfolio-data.reader")
    assert resolution is not None
    event = resolution_event(resolution, agent_name="router")
    assert isinstance(event, trace.TraceEvent)
    assert event.event_type == EVENT_RESOLUTION == "dns_resolution"
    assert event.payload == build_resolution_payload(resolution)


def test_event_agent_name_defaults_to_empty() -> None:
    pytest.importorskip("pyagent_trace.events")
    decision = Decision(Outcome.DENY, "X", "why", "p", Action.CALL, "c")
    assert decision_event(decision).agent_name == ""


def test_building_an_event_without_pyagent_trace_says_how_to_install_it() -> None:
    code = (
        "import sys\n"
        "sys.modules['pyagent_trace'] = None\n"
        "sys.modules['pyagent_trace.events'] = None\n"
        "from pyagent_dns.authority import Action, Decision, Outcome\n"
        "from pyagent_dns.events import decision_event\n"
        "try:\n"
        "    decision_event(Decision(Outcome.DENY, 'X', 'why', 'p', Action.CALL, 'c'))\n"
        "except ImportError as exc:\n"
        "    print(exc)\n"
    )
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")]),
    }
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=False
    )
    assert "pyagent-dns[trace]" in result.stdout, result.stderr
