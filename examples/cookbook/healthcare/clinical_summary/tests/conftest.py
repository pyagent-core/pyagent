"""Test fixtures for clinical_summary."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def accurate_mocks():
    return MockLLM(responses=[
        "Diagnoses: CHF. Meds: furosemide 40 mg BID. Allergy: penicillin.",
        "68M CHF. Furosemide 40 mg BID. Allergy: penicillin (rash).",
        "ACCURATE\nSummary matches source.",
    ])


@pytest.fixture()
def needs_correction_mocks():
    return MockLLM(responses=[
        "Diagnoses: CHF. Meds: furosemide 80 mg.",
        "68M CHF. Furosemide 80 mg.",
        "Dose incorrect — should be 40 mg. SAFETY FLAGS:\n- Wrong dose",
        "ACCURATE\nCorrected to 40 mg.",
    ])
