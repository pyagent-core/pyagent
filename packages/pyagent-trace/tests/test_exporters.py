"""Tests for all 4 trace exporters: Console, JSONL, OTel, Langfuse."""

from __future__ import annotations

import io
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pyagent_trace.events import TraceEvent, TraceEventBus
from pyagent_trace.exporters.base import TraceExporter
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter

try:
    import opentelemetry  # noqa: F401
    _HAS_OTEL = True
except ImportError:
    _HAS_OTEL = False

_skip_otel = pytest.mark.skipif(not _HAS_OTEL, reason="opentelemetry not installed")


def _make_event(**kwargs) -> TraceEvent:
    defaults = {
        "timestamp": time.time(),
        "event_type": "llm_call",
        "agent_name": "test_agent",
        "pattern_type": "pipeline",
        "payload": {"model": "gpt-4o", "tokens": 100},
    }
    defaults.update(kwargs)
    return TraceEvent(**defaults)


# --- ConsoleExporter ---


def test_console_exporter_writes_stdout():
    """ConsoleExporter prints formatted events."""
    buf = io.StringIO()
    exporter = ConsoleExporter(output=buf)
    event = _make_event()
    exporter.export_event(event)

    output = buf.getvalue()
    assert "[llm_call]" in output
    assert "agent=test_agent" in output
    assert "pattern=pipeline" in output


def test_console_exporter_minimal_event():
    """ConsoleExporter handles events with no agent/pattern."""
    buf = io.StringIO()
    exporter = ConsoleExporter(output=buf)
    event = TraceEvent(timestamp=1.0, event_type="test")
    exporter.export_event(event)

    output = buf.getvalue()
    assert "[test]" in output
    assert "agent=" not in output
    assert "pattern=" not in output


def test_console_exporter_flush():
    """ConsoleExporter.flush() does not raise."""
    buf = io.StringIO()
    exporter = ConsoleExporter(output=buf)
    exporter.flush()


def test_console_exporter_shutdown():
    """ConsoleExporter.shutdown() flushes."""
    buf = io.StringIO()
    exporter = ConsoleExporter(output=buf)
    exporter.export_event(_make_event())
    exporter.shutdown()
    assert len(buf.getvalue()) > 0


# --- JsonlExporter ---


def test_jsonl_exporter_writes_file():
    """JsonlExporter creates valid JSONL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "trace.jsonl"
        exporter = JsonlExporter(path)

        exporter.export_event(_make_event(event_type="pattern_start"))
        exporter.export_event(_make_event(event_type="llm_call"))
        exporter.flush()

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert "event_type" in data
            assert "timestamp" in data


def test_jsonl_exporter_creates_parent_dirs():
    """JsonlExporter creates parent directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "sub" / "dir" / "trace.jsonl"
        exporter = JsonlExporter(path)
        exporter.export_event(_make_event())
        exporter.flush()
        assert path.exists()


def test_jsonl_exporter_flush():
    """Flush writes buffered events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "trace.jsonl"
        exporter = JsonlExporter(path)
        exporter.export_event(_make_event())
        exporter.flush()
        assert path.stat().st_size > 0


def test_jsonl_exporter_shutdown():
    """Shutdown flushes and closes the file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "trace.jsonl"
        exporter = JsonlExporter(path)
        exporter.export_event(_make_event())
        exporter.shutdown()
        assert path.stat().st_size > 0
        # After shutdown, file should be closed
        assert exporter._file is not None
        assert exporter._file.closed


def test_jsonl_exporter_shutdown_without_open():
    """Shutdown when file was never opened is a no-op."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "trace.jsonl"
        exporter = JsonlExporter(path)
        exporter.shutdown()  # should not raise


def test_jsonl_exporter_flush_without_open():
    """Flush when file was never opened is a no-op."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "trace.jsonl"
        exporter = JsonlExporter(path)
        exporter.flush()  # should not raise


# --- OTelExporter ---


@_skip_otel
def test_otel_exporter_creates_span():
    """OTelExporter creates OTel span with correct attributes."""
    from pyagent_trace.exporters.otel import OTelExporter

    with patch("pyagent_trace.exporters.otel.trace") as mock_trace:
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer
        mock_tracer.start_span.return_value = mock_span
        mock_trace.StatusCode = trace_status_mock()

        exporter = OTelExporter()
        event = _make_event(payload={"cost_usd": 0.005, "model": "gpt-4o"})
        exporter.export_event(event)

        mock_tracer.start_span.assert_called_once()
        mock_span.end.assert_called_once()


@_skip_otel
def test_otel_exporter_maps_event_types():
    """Each event_type maps to a correct span name."""
    from pyagent_trace.exporters.otel import _SPAN_NAME_MAP

    for event_type in [
        "pattern_start", "pattern_end", "agent_start", "agent_end",
        "llm_call", "llm_response", "routing_decision", "compression",
        "error", "cost_record",
    ]:
        assert event_type in _SPAN_NAME_MAP


@_skip_otel
def test_otel_exporter_error_event():
    """OTelExporter sets ERROR status for error events."""
    from pyagent_trace.exporters.otel import OTelExporter

    with patch("pyagent_trace.exporters.otel.trace") as mock_trace:
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer
        mock_tracer.start_span.return_value = mock_span
        mock_trace.StatusCode = trace_status_mock()

        exporter = OTelExporter()
        event = _make_event(event_type="error", payload={"message": "boom"})
        exporter.export_event(event)

        mock_span.set_status.assert_called()


@_skip_otel
def test_otel_exporter_flush():
    """OTelExporter.flush() is a no-op."""
    from pyagent_trace.exporters.otel import OTelExporter

    with patch("pyagent_trace.exporters.otel.trace") as mock_trace:
        mock_trace.get_tracer.return_value = MagicMock()
        exporter = OTelExporter()
        exporter.flush()  # should not raise


@_skip_otel
def test_otel_exporter_shutdown():
    """OTelExporter.shutdown() is a no-op."""
    from pyagent_trace.exporters.otel import OTelExporter

    with patch("pyagent_trace.exporters.otel.trace") as mock_trace:
        mock_trace.get_tracer.return_value = MagicMock()
        exporter = OTelExporter()
        exporter.shutdown()  # should not raise


def test_otel_exporter_missing_package():
    """OTelExporter raises ImportError if opentelemetry not installed."""
    from pyagent_trace.exporters.otel import OTelExporter

    with patch("pyagent_trace.exporters.otel._HAS_OTEL", False):
        with pytest.raises(ImportError, match="opentelemetry package not installed"):
            OTelExporter()


# --- LangfuseExporter ---


def test_langfuse_exporter_creates_trace():
    """pattern_start creates langfuse.trace()."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    mock_trace_obj = MagicMock()
    mock_client.trace.return_value = mock_trace_obj

    exporter = LangfuseExporter(client=mock_client)
    event = _make_event(
        event_type="pattern_start",
        pattern_type="debate",
        payload={"trace_id": "t1"},
    )
    exporter.export_event(event)

    mock_client.trace.assert_called_once()
    assert "t1" in exporter._active_traces


def test_langfuse_exporter_creates_span():
    """agent_start creates trace.span()."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    mock_trace_obj = MagicMock()
    mock_span = MagicMock()
    mock_client.trace.return_value = mock_trace_obj
    mock_trace_obj.span.return_value = mock_span

    exporter = LangfuseExporter(client=mock_client)

    # Start a pattern first
    exporter.export_event(_make_event(
        event_type="pattern_start",
        pattern_type="debate",
        payload={"trace_id": "t1"},
    ))

    # Then start agent
    exporter.export_event(_make_event(
        event_type="agent_start",
        agent_name="bull",
        pattern_type="debate",
        payload={"trace_id": "t1"},
    ))

    mock_trace_obj.span.assert_called_once()


def test_langfuse_exporter_creates_generation():
    """llm_call creates trace.generation()."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    mock_trace_obj = MagicMock()
    mock_client.trace.return_value = mock_trace_obj

    exporter = LangfuseExporter(client=mock_client)

    # Start pattern
    exporter.export_event(_make_event(
        event_type="pattern_start",
        pattern_type="debate",
        payload={"trace_id": "t1"},
    ))

    # LLM call
    exporter.export_event(_make_event(
        event_type="llm_call",
        agent_name="bull",
        pattern_type="debate",
        payload={
            "trace_id": "t1",
            "model": "gpt-4o",
            "messages_in": [{"role": "user", "content": "test"}],
            "response": "Response text",
            "input_tokens": 100,
            "output_tokens": 50,
        },
    ))

    mock_trace_obj.generation.assert_called_once()


def test_langfuse_exporter_pattern_end():
    """pattern_end updates and removes active trace."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    mock_trace_obj = MagicMock()
    mock_client.trace.return_value = mock_trace_obj

    exporter = LangfuseExporter(client=mock_client)

    exporter.export_event(_make_event(
        event_type="pattern_start",
        pattern_type="debate",
        payload={"trace_id": "t1"},
    ))
    exporter.export_event(_make_event(
        event_type="pattern_end",
        pattern_type="debate",
        payload={"trace_id": "t1"},
    ))

    mock_trace_obj.update.assert_called_once()
    assert "t1" not in exporter._active_traces


def test_langfuse_exporter_agent_end():
    """agent_end removes active span."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    mock_trace_obj = MagicMock()
    mock_span = MagicMock()
    mock_client.trace.return_value = mock_trace_obj
    mock_trace_obj.span.return_value = mock_span

    exporter = LangfuseExporter(client=mock_client)

    exporter.export_event(_make_event(
        event_type="pattern_start",
        pattern_type="debate",
        payload={"trace_id": "t1"},
    ))
    exporter.export_event(_make_event(
        event_type="agent_start",
        agent_name="bull",
        payload={"trace_id": "t1"},
    ))
    exporter.export_event(_make_event(
        event_type="agent_end",
        agent_name="bull",
        payload={"trace_id": "t1"},
    ))

    mock_span.end.assert_called_once()
    assert "bull" not in exporter._active_spans


def test_langfuse_exporter_cost_record():
    """cost_record updates trace with cost metadata."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    mock_trace_obj = MagicMock()
    mock_client.trace.return_value = mock_trace_obj

    exporter = LangfuseExporter(client=mock_client)

    exporter.export_event(_make_event(
        event_type="pattern_start",
        pattern_type="debate",
        payload={"trace_id": "t1"},
    ))
    exporter.export_event(_make_event(
        event_type="cost_record",
        pattern_type="debate",
        payload={"trace_id": "t1", "cost_usd": 0.005},
    ))

    mock_trace_obj.update.assert_called_once()


def test_langfuse_exporter_shutdown_flushes():
    """Shutdown calls langfuse.flush()."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    exporter = LangfuseExporter(client=mock_client)
    exporter.shutdown()

    mock_client.flush.assert_called_once()


def test_langfuse_exporter_flush():
    """Flush calls langfuse.flush()."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    exporter = LangfuseExporter(client=mock_client)
    exporter.flush()

    mock_client.flush.assert_called_once()


def test_langfuse_exporter_missing_package():
    """LangfuseExporter raises ImportError if langfuse not installed."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    with patch("pyagent_trace.exporters.langfuse.Langfuse", None):
        with pytest.raises(ImportError, match="langfuse package not installed"):
            LangfuseExporter(public_key="pk", secret_key="sk")


def test_langfuse_exporter_unhandled_event_type():
    """Unhandled event types are silently ignored."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    mock_client = MagicMock()
    exporter = LangfuseExporter(client=mock_client)
    exporter.export_event(_make_event(event_type="unknown_type"))
    # No error, no mock calls for trace/span/generation


# --- Protocol conformance ---


def test_exporter_protocol_conformance():
    """All available exporters satisfy TraceExporter protocol."""
    from pyagent_trace.exporters.langfuse import LangfuseExporter

    exporters: list[object] = [
        ConsoleExporter(output=io.StringIO()),
        JsonlExporter(Path(tempfile.mkdtemp()) / "test.jsonl"),
        LangfuseExporter(client=MagicMock()),
    ]

    if _HAS_OTEL:
        from pyagent_trace.exporters.otel import OTelExporter

        with patch("pyagent_trace.exporters.otel.trace") as mock_trace:
            mock_trace.get_tracer.return_value = MagicMock()
            exporters.append(OTelExporter())

    for exp in exporters:
        assert isinstance(exp, TraceExporter), f"{type(exp).__name__} does not conform"
        assert callable(exp.export_event)
        assert callable(exp.flush)
        assert callable(exp.shutdown)


# --- Multi-export via bus ---


def test_multi_export_via_bus():
    """Bus with 3 exporters subscribed, all receive events."""
    buf = io.StringIO()
    console = ConsoleExporter(output=buf)

    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = Path(tmpdir) / "trace.jsonl"
        jsonl = JsonlExporter(jsonl_path)

        collector: list[TraceEvent] = []

        bus = TraceEventBus()
        bus.subscribe(console.export_event)
        bus.subscribe(jsonl.export_event)
        bus.subscribe(collector.append)

        event = _make_event()
        bus.emit(event)

        # Console received
        assert "[llm_call]" in buf.getvalue()
        # JSONL received
        jsonl.flush()
        assert jsonl_path.stat().st_size > 0
        # Collector received
        assert len(collector) == 1


# --- Helpers ---


def trace_status_mock():
    """Create a mock StatusCode enum."""
    mock = MagicMock()
    mock.OK = "OK"
    mock.ERROR = "ERROR"
    return mock
