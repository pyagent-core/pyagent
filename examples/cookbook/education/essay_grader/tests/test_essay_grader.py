"""Tests for essay grader mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import Voting
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    grader = Voting(
        voters=[Agent(f"grader_{p}", llm, system_prompt="") for p in ["openai", "anthropic", "gemini"]],
        strategy="majority",
    )
    return BoundedExecution(pattern=grader,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_grade_a_consensus(grade_a_responses, sample_essay=None):
    safe = _build_mock(grade_a_responses)
    result = asyncio.run(safe.run("Title: AI in Education\n\nAI transforms learning..."))
    assert result.output


def test_grade_c_consensus(grade_c_responses):
    safe = _build_mock(grade_c_responses)
    result = asyncio.run(safe.run("Short essay with little content"))
    assert result.output


def test_voting_strategy_majority():
    responses = [
        "Grade: B. Good effort. Score: 82/100.",
        "Grade: B. Clear structure. Score: 80/100.",
        "Grade: A. Excellent analysis. Score: 91/100.",
    ]
    safe = _build_mock(responses)
    result = asyncio.run(safe.run("Essay text here..."))
    assert result.output


def test_cost_tracker_three_graders(bus, tracker):
    tracker.record("voting", "grader_openai",     "gpt-4o-mini",             250, 100, 0.00075)
    tracker.record("voting", "grader_anthropic",  "claude-sonnet-4-20250514", 250, 100, 0.00195)
    tracker.record("voting", "grader_gemini",     "gemini-2.0-flash",         250, 100, 0.00050)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00320, abs=1e-5)
    assert set(s["by_agent"].keys()) == {"grader_openai", "grader_anthropic", "grader_gemini"}
