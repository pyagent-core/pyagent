"""Trace event types, payload builders, and OpenTelemetry attribute keys for pyagent-dns."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyagent_dns.authority import Decision
    from pyagent_dns.resolver import Resolution

EVENT_RESOLUTION = "dns_resolution"
EVENT_DECISION = "authority_decision"
EVENT_REVOCATION = "authority_revocation"
EVENT_DELEGATION = "delegation_issued"
"""Reserved event type names. ``authority_revocation`` and ``delegation_issued`` are defined
so their strings are stable, but nothing emits them in 0.1: the graph and registry have no
event bus. Only ``dns_resolution`` and ``authority_decision`` are produced."""


class DnsAttributes:
    """OpenTelemetry attribute keys, namespaced like ``PyAgentAttributes`` in pyagent-trace."""

    RECORD_NAME = "pyagent.dns.record_name"
    RECORD_VERSION = "pyagent.dns.record_version"
    RECORD_FINGERPRINT = "pyagent.dns.record_fingerprint"
    DECISION_OUTCOME = "pyagent.dns.decision_outcome"
    DECISION_REASON_CODE = "pyagent.dns.decision_reason_code"
    GRANT_PATH = "pyagent.dns.grant_path"
    EFFECTIVE_MAX_RECORDS = "pyagent.dns.effective_max_records"


def build_resolution_payload(resolution: Resolution) -> dict[str, Any]:
    """Return the payload of a ``dns_resolution`` event."""
    return {
        "record_name": resolution.record.name,
        "record_version": resolution.version,
        "record_fingerprint": resolution.fingerprint,
        "status": str(resolution.status),
        "verified": resolution.verified,
        "verification_status": str(resolution.verification),
        "from_cache": resolution.from_cache,
        "resolved_at": resolution.resolved_at,
    }


def build_decision_payload(decision: Decision) -> dict[str, Any]:
    """Return the payload of an ``authority_decision`` event.

    It carries everything needed to answer "why was this call allowed or denied": the record
    name, version, fingerprint and verification status, the grant path and policy versions,
    effective limits, obligations, the outcome and its reason code, and the approval binding.
    It never carries the request itself, only its hash.
    """
    payload = decision.to_dict()
    payload["verification_status"] = payload.pop("record_verification")
    return payload


def _trace_event(event_type: str, agent_name: str, payload: dict[str, Any]) -> Any:
    try:
        from pyagent_trace.events import TraceEvent
    except ImportError as exc:
        raise ImportError(
            "pyagent-trace is required to build trace events. Install 'pyagent-dns[trace]'."
        ) from exc
    return TraceEvent(
        timestamp=time.time(), event_type=event_type, agent_name=agent_name, payload=payload
    )


def resolution_event(resolution: Resolution, *, agent_name: str = "") -> Any:
    """Build a ``TraceEvent`` for a resolution.

    Raises:
        ImportError: If pyagent-trace is not installed.
    """
    return _trace_event(EVENT_RESOLUTION, agent_name, build_resolution_payload(resolution))


def decision_event(decision: Decision, *, agent_name: str = "") -> Any:
    """Build a ``TraceEvent`` for an authorization decision.

    Raises:
        ImportError: If pyagent-trace is not installed.
    """
    return _trace_event(EVENT_DECISION, agent_name, build_decision_payload(decision))
