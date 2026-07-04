"""Pydantic models for Customer Support Router."""
from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel


class SupportRequest(BaseModel):
    ticket_id: str
    query: str


class SupportResponse(BaseModel):
    ticket_id: str
    intent: str
    reply: str
    escalated: bool
    zendesk_ticket_id: str | None = None
    cost_usd: float
    trace_file: str


def parse_intent(output: str) -> Literal["billing", "technical", "account", "escalate"]:
    out = output.strip().lower()
    for intent in ("billing", "technical", "account", "escalate"):
        if intent in out:
            return intent  # type: ignore[return-value]
    return "escalate"


def _create_zendesk_ticket(summary: str, priority: str) -> str:
    import httpx, os
    r = httpx.post(
        os.environ["ZENDESK_URL"] + "/api/v2/tickets.json",
        json={"ticket": {"subject": summary[:80], "priority": priority,
                         "comment": {"body": summary}}},
        auth=(os.environ["ZENDESK_EMAIL"] + "/token", os.environ["ZENDESK_TOKEN"]),
        timeout=15.0,
    )
    r.raise_for_status()
    return str(r.json()["ticket"]["id"])
