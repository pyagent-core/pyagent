"""Test fixtures for research_assistant."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def gather_mocks():
    return MockLLM(responses=[
        "[web]: LLMs now score 80% on reasoning benchmarks.",
        "[arxiv]: 3 papers show chain-of-thought improves reasoning.",
        "[news]: OpenAI and Anthropic both focused on reasoning.",
        "Balanced: strong progress but planning still limited.",
    ])


@pytest.fixture()
def debate_mocks():
    return MockLLM(responses=[
        "Optimist: LLMs solve complex reasoning at near-human levels.",
        "Sceptic: benchmarks don't transfer to real planning tasks.",
        "Verdict: progress is real but gaps remain in multi-step planning.",
    ])
