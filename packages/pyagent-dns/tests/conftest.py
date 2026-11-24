"""Shared fixtures for pyagent-dns tests.

Signing keys are generated at test time into a temp directory. No private key is committed.
Time is injected through ``frozen_clock``, so no test sleeps.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from pyagent_dns.authority import (
    Action,
    AuthorityGraph,
    CallContext,
    Decision,
    DelegationTerms,
    Grant,
    GrantEffect,
    Limits,
    ResourceSelector,
)
from pyagent_dns.records import Identity, NameRecord, RecordKind, RecordStatus
from pyagent_dns.registry import NameRegistry
from pyagent_dns.resolver import Resolver
from pyagent_dns.signing import (
    TrustedKey,
    TrustedKeys,
    fingerprint_of_public_key,
    generate_keypair,
    load_private_key,
    sign_record,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from cryptography.hazmat.primitives.asymmetric import ed25519

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
"""The instant ``frozen_clock`` starts at."""


class ControllableClock:
    """An epoch-seconds clock that only moves when told to."""

    def __init__(self, start: datetime = T0) -> None:
        self._now = start.timestamp()

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds

    def now_utc(self) -> datetime:
        return datetime.fromtimestamp(self._now, UTC)


@pytest.fixture
def frozen_clock() -> ControllableClock:
    return ControllableClock()


@pytest.fixture(scope="session")
def session_keypair(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[ed25519.Ed25519PrivateKey, str, str]:
    """A throwaway Ed25519 keypair: (private key, public key PEM, fingerprint)."""
    private_path, public_path = generate_keypair(tmp_path_factory.mktemp("keys"))
    public_pem = public_path.read_text(encoding="utf-8")
    return load_private_key(private_path), public_pem, fingerprint_of_public_key(public_pem)


@pytest.fixture
def private_key(session_keypair: Any) -> ed25519.Ed25519PrivateKey:
    key: ed25519.Ed25519PrivateKey = session_keypair[0]
    return key


@pytest.fixture
def public_key_pem(session_keypair: Any) -> str:
    pem: str = session_keypair[1]
    return pem


@pytest.fixture
def public_key_fingerprint(session_keypair: Any) -> str:
    fingerprint: str = session_keypair[2]
    return fingerprint


@pytest.fixture
def signer_name() -> str:
    return "platform_registry"


@pytest.fixture
def trusted_keys(signer_name: str, public_key_pem: str, public_key_fingerprint: str) -> TrustedKeys:
    return TrustedKeys([TrustedKey(signer_name, public_key_fingerprint, public_key_pem)])


@pytest.fixture
def make_record(
    private_key: ed25519.Ed25519PrivateKey,
    signer_name: str,
    public_key_pem: str,
    public_key_fingerprint: str,
) -> Callable[..., NameRecord]:
    """Build a NameRecord signed by the trusted test key.

    Any field can be overridden by keyword. ``sign=False`` returns it unsigned, and
    ``tamper=True`` returns it signed and then altered, so its signature no longer verifies.
    """

    def factory(
        name: str = "portfolio-data.reader",
        *,
        kind: RecordKind = RecordKind.TOOL,
        version: str = "3.2.1",
        capabilities: tuple[str, ...] = ("read_positions", "read_holdings"),
        data_classes: tuple[str, ...] = ("internal",),
        status: RecordStatus = RecordStatus.ACTIVE,
        expires: datetime | None = None,
        sign: bool = True,
        tamper: bool = False,
        **overrides: Any,
    ) -> NameRecord:
        fields: dict[str, Any] = {
            "endpoint": f"https://internal.example/{name}",
            "identity": Identity(
                public_key_fingerprint=public_key_fingerprint,
                public_key=public_key_pem,
                signed_by=signer_name,
            ),
            "schema_hash": "sha256:" + "ab" * 32,
            "owner": "wealth_platform_team",
        } | overrides
        record = NameRecord(
            name=name,
            kind=kind,
            version=version,
            capabilities=capabilities,
            data_classes=data_classes,
            status=status,
            expires=expires,
            **fields,
        )
        if sign:
            record = sign_record(record, private_key)
        if tamper:
            record = dataclasses.replace(record, endpoint="https://attacker.example/leak")
        return record

    return factory


@pytest.fixture
def registry(
    make_record: Callable[..., NameRecord],
    trusted_keys: TrustedKeys,
    frozen_clock: ControllableClock,
) -> NameRegistry:
    """Three verified records: internal, confidential, and public data."""
    reg = NameRegistry(trusted_keys, clock=frozen_clock)
    reg.register_many(
        [
            make_record("portfolio-data.reader", capabilities=("read_positions", "read_holdings")),
            make_record(
                "client-vault-reader", capabilities=("read_vault",), data_classes=("confidential",)
            ),
            make_record(
                "public-docs.reader", capabilities=("read_docs",), data_classes=("public",)
            ),
        ]
    )
    return reg


@pytest.fixture
def resolver(registry: NameRegistry) -> Resolver:
    return Resolver(registry)


@pytest.fixture
def graph(registry: NameRegistry) -> AuthorityGraph:
    """Grants for ``research_agent``: call the portfolio reader, read public docs, and export
    portfolio data only with approval. Nothing at all for ``client-vault-reader``."""
    g = AuthorityGraph(registry)
    g.add_grants(
        [
            Grant(
                grant_id="g_portfolio",
                principal="research_agent",
                action=Action.CALL,
                capability="portfolio-data.reader",
                resource=ResourceSelector(data_classes=("internal",)),
                purpose="portfolio_review",
                limits=Limits(max_records_per_call=500, max_calls_per_session=20),
                policy_version="v14",
            ),
            Grant(
                grant_id="g_public",
                principal="research_agent",
                action=Action.READ,
                capability="public-docs.reader",
                resource=ResourceSelector(data_classes=("public",)),
                purpose="portfolio_review",
            ),
            Grant(
                grant_id="g_export",
                principal="research_agent",
                action=Action.EXPORT,
                capability="portfolio-data.reader",
                resource=ResourceSelector(data_classes=("confidential",)),
                purpose="portfolio_review",
                effect=GrantEffect.REQUIRE_APPROVAL,
                approver_role="data_owner",
            ),
        ]
    )
    return g


@pytest.fixture
def ask(graph: AuthorityGraph, resolver: Resolver) -> Callable[..., Decision]:
    """Ask the graph whether a call is allowed, resolving the record the way middleware does.

    Defaults describe the golden call. Keyword arguments beyond the named ones fill the
    ``CallContext``; ``chain`` replaces the principal chain.
    """

    def _ask(
        capability: str = "portfolio-data.reader",
        *,
        action: Action = Action.CALL,
        principal: str = "research_agent",
        chain: list[str] | None = None,
        purpose: str = "portfolio_review",
        resource: ResourceSelector | None = None,
        **context: Any,
    ) -> Decision:
        return graph.authorize(
            chain or [principal],
            action,
            capability,
            resource or ResourceSelector(),
            CallContext(purpose=purpose, **context),
            resolver.resolve_fresh(capability),
        )

    return _ask


@pytest.fixture
def delegable() -> Callable[..., Grant]:
    """Build a delegable grant for ``lead``. ``must_attenuate`` defaults to False so a test
    can delegate an equal scope; override any field by keyword."""

    def factory(grant_id: str = "root", *, must_attenuate: bool = False, **fields: Any) -> Grant:
        defaults: dict[str, Any] = {
            "principal": "lead",
            "action": Action.CALL,
            "capability": "portfolio-data.reader",
            "resource": ResourceSelector(data_classes=("internal",)),
            "purpose": "portfolio_review",
            "delegation": DelegationTerms(allowed=True, must_attenuate=must_attenuate),
        }
        return Grant(grant_id=grant_id, **(defaults | fields))

    return factory
