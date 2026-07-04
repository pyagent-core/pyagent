"""Trading Signals test fixtures."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def bullish_mock():
    return MockLLM(responses=[
        "Signal: BUY, strength: 4/5. Price above all MAs, RSI rising.",
        "Signal: NEUTRAL, strength: 2/5. RSI 71 approaching overbought.",
        "Signal: BUY, strength: 5/5. Put/call 0.55, VIX 18, upgrades.",
        "Consensus: LONG, conviction: 7/10. Momentum + sentiment outweigh mean-reversion caution.",
    ])


@pytest.fixture()
def bearish_mock():
    return MockLLM(responses=[
        "Signal: SELL, strength: 4/5. Price below 200-day MA, volume declining.",
        "Signal: BUY, strength: 3/5. RSI 28, oversold territory.",
        "Signal: SELL, strength: 4/5. Put/call 1.8, VIX spiking.",
        "Consensus: SHORT, conviction: 6/10. Momentum + sentiment dominate despite MR signal.",
    ])
