"""Tests for pyagent-trace: CostTracker, Recorder, PyAgentAttributes."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pyagent_patterns.base import Message, Role
from pyagent_trace.attributes import PyAgentAttributes
from pyagent_trace.cost import CostTracker
from pyagent_trace.recorder import Recorder

# --- PyAgentAttributes ---


def test_attributes_pattern_keys():
    assert PyAgentAttributes.PATTERN_TYPE == "pyagent.pattern.type"
    assert PyAgentAttributes.PATTERN_ROUNDS == "pyagent.pattern.rounds"
    assert PyAgentAttributes.PATTERN_ESCALATED == "pyagent.pattern.escalated"


def test_attributes_router_keys():
    assert PyAgentAttributes.ROUTER_DIFFICULTY == "pyagent.router.difficulty"
    assert PyAgentAttributes.ROUTER_SELECTED_MODEL == "pyagent.router.selected_model"


def test_attributes_compress_keys():
    assert PyAgentAttributes.COMPRESS_SAVINGS_PCT == "pyagent.compress.savings_pct"


def test_attributes_cost_keys():
    assert PyAgentAttributes.COST_TOTAL_USD == "pyagent.cost.total_usd"
    assert PyAgentAttributes.COST_MODEL == "pyagent.cost.model"


def test_attributes_exec_keys():
    assert PyAgentAttributes.EXEC_DURATION_MS == "pyagent.exec.duration_ms"
    assert PyAgentAttributes.EXEC_LLM_CALLS == "pyagent.exec.llm_calls"


# --- CostTracker ---


def test_cost_tracker_empty():
    tracker = CostTracker()
    assert tracker.total_cost == 0.0
    assert tracker.total_tokens == 0
    assert tracker.by_pattern() == {}
    assert tracker.by_agent() == {}
    assert tracker.by_model() == {}


def test_cost_tracker_record_and_totals():
    tracker = CostTracker()
    tracker.record("debate", "bull", "gpt-4o", 500, 200, 0.003)
    tracker.record("debate", "bear", "gpt-4o-mini", 500, 200, 0.0004)
    tracker.record("debate", "judge", "gpt-4o", 1000, 300, 0.0055)

    assert tracker.total_cost == pytest.approx(0.0089, abs=1e-6)
    assert tracker.total_tokens == 2700


def test_cost_tracker_by_pattern():
    tracker = CostTracker()
    tracker.record("debate", "bull", "gpt-4o", 100, 50, 0.002)
    tracker.record("pipeline", "stage1", "gpt-4o-mini", 100, 50, 0.0005)

    by_p = tracker.by_pattern()
    assert "debate" in by_p
    assert "pipeline" in by_p
    assert by_p["debate"] == pytest.approx(0.002)
    assert by_p["pipeline"] == pytest.approx(0.0005)


def test_cost_tracker_by_agent():
    tracker = CostTracker()
    tracker.record("debate", "bull", "gpt-4o", 100, 50, 0.002)
    tracker.record("debate", "bull", "gpt-4o", 100, 50, 0.002)
    tracker.record("debate", "bear", "gpt-4o", 100, 50, 0.001)

    by_a = tracker.by_agent()
    assert by_a["bull"] == pytest.approx(0.004)
    assert by_a["bear"] == pytest.approx(0.001)


def test_cost_tracker_by_model():
    tracker = CostTracker()
    tracker.record("p", "a", "gpt-4o", 100, 50, 0.003)
    tracker.record("p", "b", "gpt-4o-mini", 100, 50, 0.0003)

    by_m = tracker.by_model()
    assert "gpt-4o" in by_m
    assert "gpt-4o-mini" in by_m


def test_cost_tracker_summary():
    tracker = CostTracker()
    tracker.record("debate", "bull", "gpt-4o", 500, 200, 0.003)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.003)
    assert s["total_tokens"] == 700
    assert s["entries"] == 1


# --- Recorder ---


def test_recorder_start_end():
    rec = Recorder()
    rec.start("debate")
    rec.end("Final output")
    assert len(rec.entries) == 2
    assert rec.entries[0].event_type == "pattern_start"
    assert rec.entries[1].event_type == "pattern_end"
    assert rec.entries[1].response == "Final output"


def test_recorder_record_llm_call():
    rec = Recorder()
    rec.start("pipeline")
    messages = [Message(role=Role.USER, content="Hello")]
    rec.record_llm_call("agent1", messages, "Response text")
    rec.end("done")

    assert len(rec.llm_calls) == 1
    call = rec.llm_calls[0]
    assert call.agent_name == "agent1"
    assert call.response == "Response text"
    assert call.messages_in[0]["role"] == "user"
    assert call.messages_in[0]["content"] == "Hello"


def test_recorder_save_and_load():
    rec = Recorder()
    rec.start("voting")
    messages = [Message(role=Role.USER, content="Vote please")]
    rec.record_llm_call("voter1", messages, "YES")
    rec.record_llm_call("voter2", messages, "NO")
    rec.end("YES wins")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "trace.jsonl"
        rec.save(path)

        # Verify file exists and is valid JSONL
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 4  # start + 2 calls + end

        for line in lines:
            data = json.loads(line)
            assert "event_type" in data
            assert "timestamp" in data

        # Load and verify
        loaded = Recorder.load(path)
        assert len(loaded) == 4
        assert loaded[0].event_type == "pattern_start"
        assert loaded[1].event_type == "llm_call"
        assert loaded[1].agent_name == "voter1"
        assert loaded[2].agent_name == "voter2"
        assert loaded[3].event_type == "pattern_end"
        assert loaded[3].response == "YES wins"


def test_recorder_metadata():
    rec = Recorder()
    rec.start("debate")
    messages = [Message(role=Role.USER, content="test")]
    rec.record_llm_call("bull", messages, "Bull case", metadata={"round": 1, "position": "BUY"})
    rec.end("done")

    call = rec.llm_calls[0]
    assert call.metadata["round"] == 1
    assert call.metadata["position"] == "BUY"


def test_recorder_empty():
    rec = Recorder()
    assert rec.entries == []
    assert rec.llm_calls == []
