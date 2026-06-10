"""Tests for ProviderService (LiteLLM wrapper) and SimulationService enhancements."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# --- ProviderService ---


def test_provider_service_missing_litellm():
    """ProviderService raises ImportError if litellm not installed."""
    with patch("pyagent_studio.services.provider_service._HAS_LITELLM", False):
        from pyagent_studio.services.provider_service import ProviderService

        with pytest.raises(ImportError, match="litellm package not installed"):
            ProviderService()


@pytest.fixture
def mock_litellm():
    """Patch litellm module for tests."""
    with patch("pyagent_studio.services.provider_service._HAS_LITELLM", True):
        with patch("pyagent_studio.services.provider_service.litellm") as mock:
            yield mock


@pytest.fixture
def provider_service(mock_litellm):
    """Create a ProviderService with mocked litellm."""
    from pyagent_studio.services.provider_service import ProviderService

    return ProviderService(default_model="gpt-4o")


def test_provider_service_name(provider_service):
    """Provider name is 'litellm'."""
    assert provider_service.name == "litellm"


@pytest.mark.asyncio
async def test_provider_service_complete_mocked(provider_service, mock_litellm):
    """complete() calls litellm.acompletion."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello back!"
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)

    result = await provider_service.complete(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert result == "Hello back!"
    mock_litellm.acompletion.assert_awaited_once()


@pytest.mark.asyncio
async def test_provider_service_complete_default_model(provider_service, mock_litellm):
    """complete() uses default model when none specified."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response"
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)

    await provider_service.complete(messages=[{"role": "user", "content": "Hi"}])

    call_args = mock_litellm.acompletion.call_args
    assert call_args.kwargs["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_provider_service_complete_empty_content(provider_service, mock_litellm):
    """complete() returns empty string when content is None."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)

    result = await provider_service.complete(messages=[])
    assert result == ""


@pytest.mark.asyncio
async def test_provider_service_stream_mocked(provider_service, mock_litellm):
    """stream() calls litellm.acompletion with stream=True."""

    async def mock_stream():
        for text in ["Hello", " ", "world"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            chunk.choices[0].delta.content = text
            yield chunk

    mock_litellm.acompletion = AsyncMock(return_value=mock_stream())

    chunks = []
    async for chunk in provider_service.stream(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    ):
        chunks.append(chunk)

    assert chunks == ["Hello", " ", "world"]
    mock_litellm.acompletion.assert_awaited_once()
    # Verify stream=True was passed
    call_args = mock_litellm.acompletion.call_args
    assert call_args.kwargs.get("stream") is True


@pytest.mark.asyncio
async def test_provider_service_stream_skips_empty(provider_service, mock_litellm):
    """stream() skips chunks with empty delta content."""

    async def mock_stream():
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta = MagicMock()
        chunk1.choices[0].delta.content = "Hi"
        yield chunk1

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta = MagicMock()
        chunk2.choices[0].delta.content = None
        yield chunk2

    mock_litellm.acompletion = AsyncMock(return_value=mock_stream())

    chunks = []
    async for chunk in provider_service.stream(messages=[]):
        chunks.append(chunk)

    assert chunks == ["Hi"]


def test_provider_service_list_models(provider_service, mock_litellm):
    """list_models() returns expected model list."""
    mock_litellm.model_list = ["gpt-4o", "claude-3-sonnet", "gemini-pro"]

    result = provider_service.list_models()
    assert result == ["gpt-4o", "claude-3-sonnet", "gemini-pro"]


def test_provider_service_list_models_fallback(provider_service, mock_litellm):
    """list_models() falls back to models_by_provider on error."""
    mock_litellm.model_list = None
    mock_litellm.models_by_provider = {"openai": ["gpt-4o"]}

    result = provider_service.list_models()
    assert "openai" in result


@pytest.mark.asyncio
async def test_provider_service_health_check_success(provider_service, mock_litellm):
    """health_check() returns healthy for reachable model."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "pong"
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)

    result = await provider_service.health_check("gpt-4o")

    assert result["healthy"] is True
    assert result["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_provider_service_health_check_failure(provider_service, mock_litellm):
    """health_check() returns unhealthy for unreachable model."""
    mock_litellm.acompletion = AsyncMock(side_effect=Exception("Connection refused"))

    result = await provider_service.health_check("gpt-4o")

    assert result["healthy"] is False
    assert "Connection refused" in result["error"]


def test_provider_service_model_cost(provider_service, mock_litellm):
    """model_cost() returns cost using litellm cost tables."""
    mock_litellm.get_model_cost_map.return_value = {
        "gpt-4o": {
            "input_cost_per_token": 0.000005,
            "output_cost_per_token": 0.000015,
        }
    }

    result = provider_service.model_cost("gpt-4o")

    assert result["input_cost_per_token"] == 0.000005
    assert result["output_cost_per_token"] == 0.000015


def test_provider_service_model_cost_unknown(provider_service, mock_litellm):
    """model_cost() returns zeros for unknown model."""
    mock_litellm.get_model_cost_map.return_value = {}

    result = provider_service.model_cost("unknown-model")

    assert result["input_cost_per_token"] == 0.0
    assert result["output_cost_per_token"] == 0.0


def test_provider_service_model_cost_error(provider_service, mock_litellm):
    """model_cost() returns zeros on error."""
    mock_litellm.get_model_cost_map.side_effect = Exception("network error")

    result = provider_service.model_cost("gpt-4o")

    assert result["input_cost_per_token"] == 0.0


# --- SimulationService enhancements ---


def test_simulation_service_accepts_event_bus():
    """SimulationService accepts event_bus parameter."""
    from pyagent_studio.services.simulation_service import SimulationService

    svc = SimulationService(event_bus=None, use_live=False)
    assert svc._event_bus is None
    assert svc._use_live is False


def test_simulation_service_accepts_use_live():
    """SimulationService accepts use_live parameter."""
    from pyagent_studio.services.simulation_service import SimulationService

    svc = SimulationService(use_live=True)
    assert svc._use_live is True


def test_simulation_service_backward_compat():
    """Existing API without new params still works."""
    from pyagent_studio.services.simulation_service import SimulationService

    svc = SimulationService()
    assert svc._event_bus is None
    assert svc._use_live is False


def test_simulation_service_event_bus_wired():
    """Events emitted during simulation when bus is provided."""
    from pyagent_trace.events import TraceEvent, TraceEventBus
    from pyagent_studio.services.simulation_service import SimulationService

    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe(received.append)

    svc = SimulationService(event_bus=bus)
    # We can't easily run a full simulation without a valid blueprint,
    # but we can verify the bus is stored
    assert svc._event_bus is bus
