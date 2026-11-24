"""pyagent-dns: Agent naming plane and authority graph for multi-agent systems."""

from __future__ import annotations

from pyagent_dns.authority import (
    HIGH_RISK_ACTIONS,
    Action,
    AttenuationError,
    AuthorityGraph,
    CallContext,
    Decision,
    DelegationResult,
    DelegationTerms,
    DelegationToken,
    Grant,
    GrantEffect,
    GrantScope,
    Limits,
    Obligation,
    Outcome,
    ResourceSelector,
)
from pyagent_dns.blueprint import DnsBundle, DnsExtensionSpec, load_blueprint_dns
from pyagent_dns.middleware import (
    AuthorizationDeniedError,
    AuthorizedAgent,
    DnsMiddleware,
    SessionCounter,
)
from pyagent_dns.records import (
    Identity,
    NameRecord,
    RecordInfo,
    RecordKind,
    RecordLoadError,
    RecordStatus,
)
from pyagent_dns.registry import NameRegistry
from pyagent_dns.resolver import Resolution, Resolver
from pyagent_dns.signing import VerificationStatus

__version__ = "0.1.0"

__all__ = [
    "HIGH_RISK_ACTIONS",
    "Action",
    "AttenuationError",
    "AuthorityGraph",
    "AuthorizationDeniedError",
    "AuthorizedAgent",
    "CallContext",
    "Decision",
    "DelegationResult",
    "DelegationTerms",
    "DelegationToken",
    "DnsBundle",
    "DnsExtensionSpec",
    "DnsMiddleware",
    "Grant",
    "GrantEffect",
    "GrantScope",
    "Identity",
    "Limits",
    "NameRecord",
    "NameRegistry",
    "Obligation",
    "Outcome",
    "RecordInfo",
    "RecordKind",
    "RecordLoadError",
    "RecordStatus",
    "Resolution",
    "Resolver",
    "ResourceSelector",
    "SessionCounter",
    "VerificationStatus",
    "load_blueprint_dns",
]
