"""Pydantic models for Code Review."""
from __future__ import annotations
import re
from pydantic import BaseModel


class ReviewRequest(BaseModel):
    pr_id: str
    code: str


class ReviewResponse(BaseModel):
    pr_id: str
    verdict: str
    security_score: int
    escalated: bool
    ticket_id: str | None = None
    cost_usd: float
    trace_file: str


def parse_security_score(output: str) -> int:
    m = re.search(r"(?:security|score)[:\s]+(\d+)", output, re.IGNORECASE)
    if m:
        return min(10, max(1, int(m.group(1))))
    return 8


def _queue_human_review(summary: str) -> str:
    import httpx, os
    r = httpx.post(
        os.environ["REVIEW_QUEUE_URL"] + "/reviews",
        json={"summary": summary[:500], "priority": "high", "source": "code-review-agent"},
        headers={"Authorization": f"Bearer {os.environ['REVIEW_QUEUE_TOKEN']}"},
        timeout=15.0,
    )
    r.raise_for_status()
    return r.json()["ticket_id"]
