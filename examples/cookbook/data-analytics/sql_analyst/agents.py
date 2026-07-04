"""Agent definitions for SQL Analyst — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM


def list_tables() -> str:
    return "tables: sales(region, amount, closed_at), customers(id, region, tier)"


def describe_table(name: str) -> str:
    schemas = {
        "sales": "columns: region TEXT, amount DECIMAL, closed_at DATE",
        "customers": "columns: id INT PK, region TEXT, tier TEXT",
    }
    return schemas.get(name, f"Table '{name}' not found")


def run_sql(query: str) -> str:
    return f"[result of: {query[:80]}] → 3 rows: (West, $1.2M), (East, $0.9M), (North, $0.7M)"


TOOLS = {
    "list_tables": list_tables,
    "describe_table": describe_table,
    "run_sql": run_sql,
}

MAX_STEPS = 5


def build_agents() -> dict[str, Agent]:
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "sql_analyst": Agent(
            "sql_analyst", smart,
            system_prompt=(
                "You are an SQL analytics assistant. Reason step by step. Use tools to explore the "
                "schema and run SQL. When you have the result, answer in plain English and show the "
                "final SQL."
            ),
        ),
    }
