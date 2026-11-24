---
description: "ADR: Naming Is Not Authorization — separating capability discovery from runtime authority in multi-agent orchestration."
---

# ADR: Naming Is Not Authorization

**Status:** Accepted.

## Context

In multi-agent systems, agents need to discover tools, services, and peer agents dynamically across runtime boundaries. Early multi-agent frameworks conflate discovery with authority: if an agent can look up an endpoint by name (or find a tool in a directory), it is assumed to have permission to invoke it.

This conflation creates critical vulnerabilities:
1. **Confused Deputy Attacks**: An untrusted caller asks a trusted supervisor to run a tool on its behalf; if the supervisor can resolve the tool, it executes it, bypassing caller permissions.
2. **Shadow Tools & Namespace Pollution**: If any registered tool is callable by any agent, rogue or compromised agents can call ungranted tools simply by guessing or resolving their names.
3. **Privilege Escalation via Delegation**: When agents delegate sub-tasks, permissions must attenuate (shrink) monotonically. Without a dedicated authority graph, delegated tokens can quietly widen privileges.

## Decision

We enforce a strict **Two-Plane Separation**:
- **Plane 1 (Naming Plane)**: Handled by `NameRegistry` and `Resolver`. Maps names to cryptographically signed `NameRecords` with Ed25519 signatures, semver matching, and TTL-cached resolution. Discovery provides only identity and schema—never permission.
- **Plane 2 (Authority Plane)**: Handled by `AuthorityGraph` and `DnsMiddleware`. Evaluates explicit, directional `Grants` with downward monotonic attenuation across 8 dimensions (purpose, actions, data classes, session counts, record limits, spend amounts, expiries, delegation depth).

Resolving a name produces a verified record; attempting to call it requires a distinct, successful authorization decision by the authority graph.

## Consequences

- **Safety**: Tools cannot be invoked merely because they exist in the registry. Even if an agent guesses an endpoint name, `DnsMiddleware` halts the execution before any model tokens or tool code run.
- **Explicit Grants**: Developers must declare grants (either programmatically or via `x-pyagent:dns` in blueprint specifications). This adds design intent but prevents ambient authority.
- **Performance**: Naming resolution is cached via TTLs in memory, and authority decisions take < 0.1ms per call, adding negligible overhead to agent operations.
