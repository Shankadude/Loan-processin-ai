"""
Shared fixtures for the entire Loan Processing AI test suite.
Loads golden data and provides reusable test helpers.
"""
import json
import pytest
from pathlib import Path


GOLDEN_DATA_PATH = Path(__file__).parent / "golden_data" / "sample_documents_with_expected_outputs.json"


@pytest.fixture(scope="session")
def golden_data():
    """Loads the golden test data once per session."""
    with open(GOLDEN_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def clean_scenario(golden_data):
    """Clean salaried applicant - expected AUTO_APPROVE."""
    return golden_data["scenarios"]["clean_approval"]


@pytest.fixture(scope="session")
def income_mismatch_scenario(golden_data):
    """Income mismatch applicant - expected REVIEW."""
    return golden_data["scenarios"]["income_mismatch_review"]


@pytest.fixture(scope="session")
def fraud_scenario(golden_data):
    """Identity fraud + forged statement - expected REJECT."""
    return golden_data["scenarios"]["identity_fraud_reject"]


@pytest.fixture(scope="session")
def high_dti_scenario(golden_data):
    """High DTI overleveraged applicant - expected REJECT."""
    return golden_data["scenarios"]["high_dti_reject"]


@pytest.fixture(scope="session")
def missing_docs_scenario(golden_data):
    """Missing required documents - expected INCOMPLETE."""
    return golden_data["scenarios"]["missing_docs_incomplete"]


@pytest.fixture(scope="session")
def borderline_scenario(golden_data):
    """Borderline moderate risk - expected REVIEW."""
    return golden_data["scenarios"]["borderline_amber"]
