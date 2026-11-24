"""Where authorization is enforced: a tool guard, an agent wrapper, and the low-level check.

Failure policy, which is deliberately the opposite of the host codebase's hooks: nothing in
verification, authorization, or obligation handling is caught and turned into a proceed. A
failure there denies the call. The one place an exception is swallowed is trace emission,
because observability is best effort and enforcement is not.

``guard_tools`` is the primary surface, and the only place in PyAgent where a tool actually
executes under a guard is ReAct, whose tools are plain ``dict[str, Callable[[str], str]]``.
``wrap_agent`` governs only handoffs that go through the wrapped object, since patterns hold
direct references to their agents. ``authorize_call`` is the entry point for anything else.

Wrap order when stacking with ``RouterMiddleware``: authorization outside, routing inside.
Build the routed agent first, then pass it to ``wrap_agent``, so a denied call costs no model
selection and no LLM call.
"""

from __future__ import annotations

import dataclasses
import logging
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pyagent_patterns.base import Agent

from pyagent_dns.authority import (
    APPROVAL_DENIED,
    APPROVAL_REQUIRED,
    GRANT_FOUND,
    HIGH_RISK_ACTIONS,
    NO_RECORD,
    OBLIGATION_UNAVAILABLE,
    Action,
    CallContext,
    Decision,
    Obligation,
    Outcome,
    ResourceSelector,
)
from pyagent_dns.events import decision_event
from pyagent_dns.records import SENSITIVITY_ORDER

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyagent_patterns.base import Message

    from pyagent_dns.authority import AuthorityGraph
    from pyagent_dns.resolver import Resolver

logger = logging.getLogger(__name__)

ApproverFn = Callable[[Decision, CallContext], bool]
"""Called with a ``REQUIRE_APPROVAL`` decision. Return True to approve this exact request."""


class AuthorizationDeniedError(Exception):
    """Raised when an agent handoff is denied. ``decision`` carries the structured reason."""

    def __init__(self, decision: Decision) -> None:
        super().__init__(f"Authorization denied [{decision.reason_code}]: {decision.reason}")
        self.decision = decision


class SessionCounter:
    """Counts calls per session and capability, for ``max_calls_per_session``.

    Not thread-safe: it is a plain dict, like the registries. Sessions are only as real as
    the ids callers give them.
    """

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}

    def count(self, session_id: str, capability: str) -> int:
        """Return calls made so far in this session for this capability."""
        return self._counts.get((session_id, capability), 0)

    def increment(self, session_id: str, capability: str) -> int:
        """Record a call and return the new count."""
        key = (session_id, capability)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def reset(self, session_id: str | None = None) -> None:
        """Clear one session's counts, or every session's."""
        if session_id is None:
            self._counts.clear()
        else:
            for key in [k for k in self._counts if k[0] == session_id]:
                del self._counts[key]


class DnsMiddleware:
    """Resolve a name, check the grants, and enforce the answer at call time.

    Every decision is appended to :attr:`decisions` and, if an event bus is wired, emitted as
    an ``authority_decision`` trace event. The decision list grows for the life of the
    middleware; clear it by discarding the middleware.

    Args:
        resolver: Resolves capability names to verified records.
        graph: Grants and delegation chains.
        event_bus: Optional ``TraceEventBus``. Emission failures never block a call.
        approver: Called for ``REQUIRE_APPROVAL`` decisions. With none wired, such calls are
            denied; there is deliberately no approving default.
        redactor: A ``ContextRedactor`` for the ``REDACT`` obligation. With none wired, a call
            that carries that obligation is denied rather than returned unredacted.
        session_counter: Counter for session limits. A private one is created if omitted.
    """

    def __init__(
        self,
        resolver: Resolver,
        graph: AuthorityGraph,
        *,
        event_bus: Any = None,
        approver: ApproverFn | None = None,
        redactor: Any = None,
        session_counter: SessionCounter | None = None,
    ) -> None:
        self._resolver = resolver
        self._graph = graph
        self._event_bus = event_bus
        self._approver = approver
        self._redactor = redactor
        self._sessions = session_counter or SessionCounter()
        self._decisions: list[Decision] = []

    @property
    def decisions(self) -> list[Decision]:
        """A copy of every decision made, in order."""
        return list(self._decisions)

    def _record(self, decision: Decision) -> Decision:
        self._decisions.append(decision)
        if self._event_bus is not None:
            try:
                self._event_bus.emit(decision_event(decision, agent_name=decision.principal))
            except Exception:
                logger.debug("authority_decision event emission failed", exc_info=True)
        return decision

    def authorize_call(
        self,
        *,
        principal_chain: Sequence[str],
        action: Action,
        capability: str,
        resource: ResourceSelector,
        context: CallContext,
    ) -> Decision:
        """Resolve ``capability`` as a record name, check the grants, and record the decision.

        High-risk actions resolve fresh, bypassing the cache. Does not run approvals or
        obligations; a caller that integrates directly handles those itself.
        """
        if action in HIGH_RISK_ACTIONS:
            resolution = self._resolver.resolve_fresh(capability)
        else:
            resolution = self._resolver.resolve(capability)

        if resolution is None:
            decision = Decision(
                outcome=Outcome.DENY,
                reason_code=NO_RECORD,
                reason=f"No NameRecord found for '{capability}'",
                principal=principal_chain[-1] if principal_chain else "",
                action=action,
                capability=capability,
            )
        else:
            decision = self._graph.authorize(
                principal_chain, action, capability, resource, context, resolution
            )
        return self._record(decision)

    def _settle_approval(self, decision: Decision, context: CallContext) -> Decision:
        """Turn a ``REQUIRE_APPROVAL`` decision into a final allow or deny, and record it.

        Other outcomes pass through. The approval is bound to the request's hash, which is
        kept on the final decision.
        """
        if decision.outcome != Outcome.REQUIRE_APPROVAL:
            return decision
        if self._approver is None:
            changes: dict[str, Any] = {
                "outcome": Outcome.DENY,
                "reason_code": APPROVAL_REQUIRED,
                "reason": "The call requires approval and no approver is configured",
                "obligations": (),
            }
        elif self._approver(decision, context):
            changes = {
                "outcome": Outcome.ALLOW_WITH_OBLIGATIONS,
                "reason_code": GRANT_FOUND,
                "reason": f"Approved by approver; bound to {decision.approval_binding}",
                "obligations": (Obligation.LOG_DECISION,),
            }
        else:
            changes = {
                "outcome": Outcome.DENY,
                "reason_code": APPROVAL_DENIED,
                "reason": "The approver rejected the request",
                "obligations": (),
            }
        return self._record(dataclasses.replace(decision, **changes))

    def _unavailable(self, decision: Decision, why: str) -> AuthorizationDeniedError:
        """Record a deny for an obligation that cannot be performed, and return the error."""
        return AuthorizationDeniedError(
            self._record(
                dataclasses.replace(
                    decision,
                    outcome=Outcome.DENY,
                    reason_code=OBLIGATION_UNAVAILABLE,
                    reason=why,
                    obligations=(),
                )
            )
        )

    def _require_obligations_possible(self, decision: Decision) -> None:
        """Before running anything, deny if an obligation could not be honored afterwards."""
        if Obligation.REDACT in decision.obligations and self._redactor is None:
            raise self._unavailable(
                decision, "The call requires redaction but no redactor is configured"
            )

    def _redact(self, decision: Decision, capability: str, content: str) -> str:
        """Redact ``content`` at the highest sensitivity the decision evaluated.

        Raises:
            AuthorizationDeniedError: If redaction fails for any reason. The content is
                withheld; it is never returned unredacted.
        """
        try:
            from pyagent_context.item import ContextItem, Sensitivity

            top = max(decision.data_classes, key=SENSITIVITY_ORDER.__getitem__, default="public")
            item = ContextItem(content=content, source=capability, sensitivity=Sensitivity(top))
            redacted = self._redactor.redact_item(item)
        except Exception as exc:
            raise self._unavailable(
                decision, f"Redaction failed ({type(exc).__name__}); output withheld"
            ) from exc
        return "" if redacted is None else str(redacted.content)

    def guard_tools(
        self,
        tools: dict[str, Callable[[str], str]],
        *,
        principal_chain: Sequence[str],
        purpose: str,
        action: Action = Action.CALL,
        session_id: str | None = None,
    ) -> dict[str, Callable[[str], str]]:
        """Return ``tools`` with every function wrapped in an authorization check.

        Each dict key is resolved as a record name, so a tools dict whose keys are not
        record names is denied with ``NO_RECORD``. That is correct, and it is how drifted
        names get noticed. A denied call returns ``DENIED [REASON_CODE] reason`` instead of
        raising, because ReAct feeds the result back to the model as an observation and the
        model can replan. The denied function is never invoked.

        Limits that need request facts (``records_requested``, ``amount``) cannot be derived
        from a ReAct call's single input string, so they are enforced only through
        ``authorize_call``. Session limits are enforced here.

        Args:
            session_id: Scopes the call counter. Defaults to a fresh id per ``guard_tools``
                call, so unrelated guarded tool sets never share a count.
        """
        session = session_id or uuid.uuid4().hex
        return {
            name: self._guard(name, fn, tuple(principal_chain), purpose, action, session)
            for name, fn in tools.items()
        }

    def _guard(
        self,
        name: str,
        fn: Callable[[str], str],
        principal_chain: tuple[str, ...],
        purpose: str,
        action: Action,
        session_id: str,
    ) -> Callable[[str], str]:
        def guarded(action_input: str) -> str:
            context = CallContext(
                purpose=purpose,
                session_id=session_id,
                calls_in_session=self._sessions.count(session_id, name),
                request_payload=action_input.encode("utf-8"),
            )
            decision = self.authorize_call(
                principal_chain=principal_chain,
                action=action,
                capability=name,
                resource=ResourceSelector(),
                context=context,
            )
            try:
                decision = self._settle_approval(decision, context)
                if not decision.allowed:
                    return f"DENIED [{decision.reason_code}] {decision.reason}"
                self._require_obligations_possible(decision)
                self._sessions.increment(session_id, name)
                output = fn(action_input)
                if Obligation.REDACT in decision.obligations:
                    output = self._redact(decision, name, output)
                return output
            except AuthorizationDeniedError as denied:
                d = denied.decision
                return f"DENIED [{d.reason_code}] {d.reason}"

        return guarded

    def wrap_agent(
        self, agent: Agent, *, principal: str, purpose: str, session_id: str | None = None
    ) -> AuthorizedAgent:
        """Wrap an agent so that calling it is authorized first.

        Calling the agent counts as ``CALL`` on the capability named by ``agent.name``,
        performed by ``principal``. The check runs before the LLM call, so a denied handoff
        spends no model call. A denial raises :class:`AuthorizationDeniedError`, because a
        pattern awaiting ``agent.run`` has no channel for a deny string, and fabricating an
        assistant message would put words in the target agent's mouth.

        Only handoffs through the returned object are governed. ``Supervisor`` holds its
        routes directly, so wrapping a classifier does not govern the specialists it routes
        to: wrap the specialists.
        """
        return AuthorizedAgent(agent, self, principal, purpose, session_id)

    def wrap_all(
        self, agents: list[Agent], *, principal: str, purpose: str
    ) -> list[AuthorizedAgent]:
        """Wrap several agents with the same principal and purpose."""
        return [self.wrap_agent(a, principal=principal, purpose=purpose) for a in agents]


class AuthorizedAgent(Agent):
    """An agent whose ``run`` first checks authorization. Build with ``wrap_agent``."""

    def __init__(
        self,
        agent: Agent,
        middleware: DnsMiddleware,
        principal: str,
        purpose: str,
        session_id: str | None = None,
    ) -> None:
        super().__init__(
            name=agent.name,
            llm=agent.llm,
            system_prompt=agent.system_prompt,
            description=agent.description,
        )
        self._wrapped_agent = agent
        self._middleware = middleware
        self._principal = principal
        self._purpose = purpose
        self._session_id = session_id

    async def run(self, messages: list[Message]) -> Message:
        """Authorize, run the wrapped agent, and apply any obligation to its reply.

        Raises:
            AuthorizationDeniedError: If the call is denied, requires approval (an agent
                handoff has no request payload to bind an approval to), or an obligation
                cannot be honored.
        """
        mw = self._middleware
        decision = mw.authorize_call(
            principal_chain=[self._principal],
            action=Action.CALL,
            capability=self.name,
            resource=ResourceSelector(),
            context=CallContext(purpose=self._purpose, session_id=self._session_id),
        )
        if not decision.allowed:
            raise AuthorizationDeniedError(decision)
        mw._require_obligations_possible(decision)
        reply = await self._wrapped_agent.run(messages)
        if Obligation.REDACT in decision.obligations:
            reply = dataclasses.replace(
                reply, content=mw._redact(decision, self.name, reply.content)
            )
        return reply
