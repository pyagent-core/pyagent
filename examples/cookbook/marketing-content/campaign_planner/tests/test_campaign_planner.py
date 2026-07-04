"""Tests for campaign planner mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.parallelism import FanOutFanIn
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    planner = FanOutFanIn(
        workers=[Agent(n, llm, system_prompt="") for n in ["email", "social", "blog"]],
        aggregator=Agent("campaign_director", llm, system_prompt=""),
    )
    return BoundedExecution(pattern=planner,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_campaign_plan_generated(campaign_responses):
    safe = _build_mock(campaign_responses)
    result = asyncio.run(safe.run("AI CRM for SMB sales teams, $20k budget"))
    assert result.output


def test_three_channels_covered(campaign_responses):
    safe = _build_mock(campaign_responses)
    result = asyncio.run(safe.run("Product launch brief..."))
    assert result.output


def test_cost_tracker_three_workers(bus, tracker):
    tracker.record("fan_out_fan_in", "email_specialist",  "claude-sonnet-4-20250514", 300, 120, 0.00228)
    tracker.record("fan_out_fan_in", "social_specialist", "gpt-4o-mini",             200,  80, 0.00060)
    tracker.record("fan_out_fan_in", "blog_specialist",   "gpt-4o-mini",             250, 100, 0.00075)
    tracker.record("fan_out_fan_in", "campaign_director", "claude-sonnet-4-20250514", 400, 160, 0.00304)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00667, abs=1e-5)
    assert len(s["by_agent"]) == 4
