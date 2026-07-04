"""Tests for SQL analyst mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.advanced import ReAct
from pyagent_patterns.recovery import BoundedExecution


def _dummy_list_tables(args: str) -> str: return "orders, customers, regions"
def _dummy_run_sql(sql: str) -> str: return "[(West, 2.1M), (East, 1.8M), (South, 1.2M)]"
def _dummy_describe_table(table: str) -> str: return f"{table}: id, name, revenue, region"

MOCK_TOOLS = [_dummy_list_tables, _dummy_run_sql, _dummy_describe_table]


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    analyst = ReAct(agent=Agent("sql_analyst", llm, system_prompt=""), tools=MOCK_TOOLS, max_steps=5)
    return BoundedExecution(pattern=analyst,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_sql_query_returns_answer(sql_responses):
    safe = _build_mock(sql_responses)
    result = asyncio.run(safe.run("Top 3 regions by revenue?"))
    assert result.output


def test_final_answer_extraction(sql_responses):
    safe = _build_mock(sql_responses)
    result = asyncio.run(safe.run("Which regions had highest revenue?"))
    assert result.output


def test_cost_tracker_per_step(bus, tracker):
    tracker.record("react", "sql_analyst", "claude-sonnet-4-20250514", 400, 150, 0.00285)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00285, abs=1e-5)
    assert "sql_analyst" in s["by_agent"]
