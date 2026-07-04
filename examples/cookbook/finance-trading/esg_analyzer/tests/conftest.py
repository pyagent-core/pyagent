"""ESG Analyzer test fixtures."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def esg_mock():
    return MockLLM(responses=[
        '{"assignments": [{"worker": "ratings", "subtask": "summarize MSCI/Sustainalytics"}, '
        '{"worker": "sfdr_scorer", "subtask": "check Article 8 alignment"}]}',
        "MSCI BBB, Sustainalytics 34 (medium). Disagreement: MSCI higher than Sustainalytics.",
        "SFDR Article 8: PAI indicators partially covered. Taxonomy eligibility: 12%. Gaps: Scope 3.",
        "ESG rating: B. Strength: net-zero 2040 target. Controversy: supplier labor audit. SFDR Art 8 fit.",
    ])
