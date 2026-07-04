"""Agent definitions for Fraud Investigation — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import OpenAILLM


def build_agents() -> dict[str, Agent]:
    gpt4o = OpenAILLM("gpt-4o")
    return {
        "fraud_analyst": Agent(
            "fraud_analyst", gpt4o,
            system_prompt=(
                "You investigate fraud alerts. Reason step by step and use tools to gather evidence: "
                "look up transactions, score anomalies, and screen payees. When you have enough, write "
                "a case file: summary, evidence, risk level (Low/Medium/High), and recommended action."
            ),
        ),
    }


def transaction_lookup(account_id: str) -> str:
    """Return recent transactions for an account (replace with your ledger/API)."""
    ledger: dict[str, str] = {
        "ACC-8842": "12 txns in 24h; $9,900 ×3 to new payees; 2 logins from new country",
    }
    return ledger.get(account_id.strip(), f"No transactions found for {account_id}")


def anomaly_score(pattern: str) -> str:
    """Score a described transaction pattern 0-100 for fraud likelihood."""
    p     = pattern.lower()
    score = 30
    if "9,900" in pattern or "9900" in pattern:
        score += 35
    if "new payee" in p or "new payees" in p:
        score += 20
    if "new country" in p or "new device" in p:
        score += 15
    return f"anomaly_score={min(score, 100)} (drivers: structuring, new payees, geo)"


def sanctions_check(payee: str) -> str:
    """Check a payee against a sanctions list (replace with OFAC/PEP screening)."""
    flagged = {"shell co ltd"}
    return "MATCH — on watchlist" if payee.strip().lower() in flagged else "no sanctions match"


TOOLS = {
    "transaction_lookup": transaction_lookup,
    "anomaly_score":      anomaly_score,
    "sanctions_check":    sanctions_check,
}
MAX_STEPS = 6
