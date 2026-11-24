# pyagent-dns

A standalone PyAgent package that separates naming from authorization for multi-agent systems with signed records and attenuated authority graphs.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Architecture Extension: 🛡️ Naming & Authorization**
> A local-first, spec-driven authorization plane for agents, tools, providers, data, and approvers.
> Resolves names to cryptographically signed records and verifies authority graphs before consequential actions run.
> Part of the PyAgent ecosystem: `pip install pyagent-dns`.

## Disambiguation

`pyagent-dns` is:
- **Not AgentDNS**: It does not implement global decentralized root servers, cryptocurrency settlement, or billing tokens.
- **Not OWASP ANS or IETF DAWN**: It does not require public PKI certificate authorities or internet-wide DID federation.
- **What it is**: A local-first, in-repo implementation of the separation those standards leave open: **records describe, grants decide**.

## Install

```bash
pip install pyagent-dns                        # Core (records, Ed25519 signing, registry, graph, middleware)
pip install "pyagent-dns[trace]"               # + PyAgent trace event bus integration
pip install "pyagent-dns[context]"             # + PyAgent context sensitivity and redaction mapping
pip install "pyagent-dns[blueprint]"           # + PyAgent blueprint extension loader
pip install "pyagent-dns[all]"                 # All optional integrations
```

Depends on: `pyagent-patterns`, `pydantic`, `pyyaml`, `cryptography`.

## Why Two Planes?

In conventional agent architectures, discovering a tool or endpoint implies having permission to call it. This ambient authority creates the confused deputy problem: a high-clearance supervisor delegates to a subagent, which then invokes high-risk tools with no boundary checks.

`pyagent-dns` splits this into two independent planes:
1. **Naming Plane**: Cryptographically signed `NameRecord` objects declare capabilities, endpoints, data classes, and schema hashes.
2. **Authorization Plane**: `Grant` declarations evaluate whether a principal chain may execute a specific action on a capability for a designated purpose under strict limits.

---

## Quickstart

Every Python block below is executed by the test suite, in order, so this page cannot drift from the API.

### 1. Sign a NameRecord

```python
from pyagent_dns.records import Identity, NameRecord, RecordKind
from pyagent_dns.signing import (
    TrustedKey,
    TrustedKeys,
    fingerprint_of_public_key,
    generate_keypair,
    load_private_key,
    sign_record,
)

# Writes private_key.pem (mode 0600) and public_key.pem. Never overwrites an existing key.
private_path, public_path = generate_keypair(".keys")
public_key = public_path.read_text()
fingerprint = fingerprint_of_public_key(public_key)

record = NameRecord(
    name="portfolio-data.reader",
    kind=RecordKind.TOOL,
    version="1.0.0",
    endpoint="https://internal.bank/tools/portfolio",
    identity=Identity(
        public_key_fingerprint=fingerprint,
        public_key=public_key,
        signed_by="security_team",
    ),
    schema_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    capabilities=("read_positions", "read_holdings"),
    data_classes=("internal",),
    owner="wealth_platform_team",
)
signed_record = sign_record(record, load_private_key(private_path))
```

### 2. Register it and resolve it

A record is only as trustworthy as the keys you trust. The registry verifies against the
`TrustedKeys` you give it, never against a key carried inside the record.

```python
from pyagent_dns.registry import NameRegistry
from pyagent_dns.resolver import Resolver

trusted = TrustedKeys([TrustedKey("security_team", fingerprint, public_key)])
registry = NameRegistry(trusted)
registry.register(signed_record)

resolver = Resolver(registry)
resolution = resolver.resolve("portfolio-data.reader")
print(resolution.verification)  # verified
print(resolution.from_cache)  # False
```

Resolution is a local lookup and a signature check. It never connects to the record's endpoint.

### 3. Evaluate a grant

Resolving a name grants nothing. Permission comes only from a `Grant`.

```python
from pyagent_dns.authority import (
    Action,
    AuthorityGraph,
    CallContext,
    Grant,
    Limits,
    ResourceSelector,
)

graph = AuthorityGraph(registry)
graph.add_grant(
    Grant(
        grant_id="grant-001",
        principal="analyst_agent",
        action=Action.CALL,
        capability="portfolio-data.reader",
        resource=ResourceSelector(data_classes=("internal",)),
        purpose="portfolio_review",
        limits=Limits(max_records_per_call=500),
    )
)

decision = graph.authorize(
    ["analyst_agent"],
    Action.CALL,
    "portfolio-data.reader",
    ResourceSelector(),
    CallContext(purpose="portfolio_review", records_requested=100),
    resolution,
)
print(decision.allowed, decision.reason_code)  # True GRANT_FOUND
```

### 4. Guard ReAct tools

```python
from pyagent_dns.middleware import DnsMiddleware

middleware = DnsMiddleware(resolver, graph)
tools = {"portfolio-data.reader": lambda query: "positions: AAPL, GOOG"}

analyst_tools = middleware.guard_tools(
    tools, principal_chain=["analyst_agent"], purpose="portfolio_review"
)
print(analyst_tools["portfolio-data.reader"]("account_123"))  # positions: AAPL, GOOG

stranger_tools = middleware.guard_tools(
    tools, principal_chain=["stranger"], purpose="portfolio_review"
)
print(stranger_tools["portfolio-data.reader"]("account_123"))  # DENIED [NO_GRANT] ...
```

A denied tool is never called. The model receives the `DENIED [CODE] reason` string as its
observation, so it can replan. Every decision is kept in `middleware.decisions`.

---

## Downward-Only Delegation (Attenuation)

A grant can be delegated to a subagent, but authority can only narrow, never widen:

```python
from pyagent_dns.authority import AttenuationError, DelegationTerms, GrantScope

graph.add_grant(
    Grant(
        grant_id="grant-lead",
        principal="lead_agent",
        action=Action.CALL,
        capability="portfolio-data.reader",
        resource=ResourceSelector(data_classes=("internal",)),
        purpose="portfolio_review",
        limits=Limits(max_records_per_call=500),
        delegation=DelegationTerms(allowed=True),
    )
)

narrower = graph.delegate(
    "grant-lead",
    delegate_principal="subagent_researcher",
    scope=GrantScope(limits=Limits(max_records_per_call=100)),
)
print(narrower.grant.limits.max_records_per_call)  # 100

try:
    graph.delegate(
        "grant-lead",
        delegate_principal="subagent_researcher",
        scope=GrantScope(limits=Limits(max_records_per_call=1000)),
    )
except AttenuationError as err:
    print(f"Refused widening on: {err.dimension}")  # limits.max_records_per_call
```

---

## Known Limitations of v0.1

1. **ReAct Tool Call Surface**: Because `pyagent-patterns` executes tools by text parsing in `ReAct`, tools accept a string input. Structured argument inspection and per-call numeric limits (`records_requested`, `amount`) are evaluated via `authorize_call()`, while `guard_tools()` hashes raw string input for approval bindings.
2. **Blueprint Spec Extension**: Top-level `x-pyagent:dns` blocks are read directly from YAML via `load_blueprint_dns()`. They do not currently round-trip through `pyagent-blueprint`'s `BlueprintSpec` parser.
3. **Local Resolution**: Verification validates the authenticity and integrity of the `NameRecord`. It does not connect to remote endpoints or verify live workload identity at runtime.

---

## Full Documentation

See [pyagent.org](https://pyagent.org) for full API references, architecture guides, and cookbook examples.

<!-- pyagent-ecosystem-footer:start -->

## The PyAgent ecosystem

PyAgent is a spec-driven architecture for orchestrating multi-agent systems. Each package is independent — install
only what you need, or get everything with [`pip install pyagent-all`](https://pyagent.org/getting-started/).

| Package | What it gives you |
|---------|-------------------|
| `pyagent-blueprint` | [Declarative multi-agent blueprints](https://pyagent.org/guides/blueprint/) — compile, validate, and diff agent systems from YAML |
| `pyagent-patterns` | [Reusable multi-agent design patterns](https://pyagent.org/packages/patterns/) — Supervisor, Pipeline, ReAct, and 15 more |
| `pyagent-router` | [Difficulty-aware model routing](https://pyagent.org/guides/router/) — cost-efficient model selection per task |
| `pyagent-compress` | [Token-efficient agent compression](https://pyagent.org/guides/compression/) — inter-agent token budgets |
| `pyagent-providers` | [Multi-provider orchestration](https://pyagent.org/guides/providers/) — fallback chains and capability negotiation |
| `pyagent-context` | [Stateful agent memory](https://pyagent.org/guides/context/) — trust-aware, three-tier context ledger |
| `pyagent-trace` | [Multi-agent observability & tracing](https://pyagent.org/guides/tracing/) — pattern-aware OpenTelemetry spans |
| `pyagent-studio` | [Agent control plane dashboard](https://pyagent.org/guides/studio/) — live traces, cost, and governance |
| `pyagent-dns` | [Agent naming & authority graph](https://pyagent.org/packages/dns/) — signed records and attenuated grants |

**Learn more:**
[Design patterns](https://pyagent.org/packages/patterns/) ·
[Cookbook](https://pyagent.org/cookbook/) ·
[Get started](https://pyagent.org/getting-started/)

<!-- pyagent-ecosystem-footer:end -->

