"""
End-to-End Tests: Full Loan Scenarios
Tests 6 realistic end-to-end cases through the deterministic pipeline stages.
These tests exercise the complete chain: Extractors → Comparisons → Risk Score → Decision.
They do NOT invoke LLM/Vision APIs or the LangGraph workflow (which requires Gemini).

Run:  python -m pytest tests/e2e/test_full_loan_scenarios.py -v
"""
import json
import pytest
from pathlib import Path

from src.decision_engine.extractors import extract_declared, extract_verified, extract_liabilities
from src.decision_engine.comparison import compare_identity, compare_income, compare_employer, compare_pan
from src.decision_engine.risk_scorer import score_application
from src.schemas.decision_models import DecisionResult
from src.utils.assembly import find_missing_documents


GOLDEN_DATA_PATH = Path(__file__).parent.parent / "golden_data" / "sample_documents_with_expected_outputs.json"


def _run_deterministic_pipeline(scenario):
    """
    Runs the deterministic portion of the pipeline (Steps 3-7):
    extract → compare → score. Returns the DecisionResult.
    """
    declared = scenario["declared"]
    documents = scenario["documents"]
    payload = {"documents": documents}

    extracted_declared = extract_declared(payload)
    extracted_verified = extract_verified(payload)
    extracted_liabilities = extract_liabilities(payload)

    # Override extracted declared with golden scenario's declared values
    # (simulating what the workflow node does)
    for key in ["name", "dob", "pan_number", "employer", "net_monthly", "gross_monthly"]:
        if declared.get(key) is not None:
            extracted_declared[key] = declared[key]

    # Override verified with golden scenario's verified values
    verified = scenario.get("verified", {})
    for key in ["name", "dob", "pan_number", "employer", "payslip_net_monthly", "bank_avg_salary_credit"]:
        if verified.get(key) is not None:
            extracted_verified[key] = verified[key]

    # Override liabilities with golden scenario
    liabilities = scenario.get("liabilities", extracted_liabilities)

    # Build comparisons
    comparisons = compare_identity(extracted_declared, extracted_verified, all_docs=documents)
    comparisons.append(compare_pan(extracted_declared, extracted_verified))
    comparisons.append(compare_income(extracted_declared, extracted_verified))
    comparisons.append(compare_employer(extracted_declared, extracted_verified))

    bank_data = scenario.get("bank_statement", {})

    result = score_application(
        application_id=f"E2E-{scenario.get('label', 'TEST')[:10]}",
        declared_payload=extracted_declared,
        verified_payload=extracted_verified,
        liabilities_payload=liabilities,
        comparisons=comparisons,
        bank_statement_data=bank_data if bank_data else None,
        requested_amount=float(declared.get("loan_amount_requested", 0)),
    )
    return result


# ==========================================================================
# Scenario 1: Clean Approval
# ==========================================================================

class TestCleanApprovalE2E:
    """End-to-end: Clean salaried applicant → AUTO_APPROVE."""

    def test_routing_is_green(self, clean_scenario):
        result = _run_deterministic_pipeline(clean_scenario)
        assert result.routing_color == "GREEN"

    def test_recommendation_auto_approve(self, clean_scenario):
        result = _run_deterministic_pipeline(clean_scenario)
        assert result.recommendation == "AUTO_APPROVE"

    def test_risk_level_low(self, clean_scenario):
        result = _run_deterministic_pipeline(clean_scenario)
        assert result.risk_level == "LOW"

    def test_risk_score_above_80(self, clean_scenario):
        result = _run_deterministic_pipeline(clean_scenario)
        expected = clean_scenario["expected_outputs"]
        assert result.risk_score >= expected["risk_score_min"]

    def test_identity_match(self, clean_scenario):
        result = _run_deterministic_pipeline(clean_scenario)
        assert result.identity_status == "MATCH"

    def test_eligibility_passed(self, clean_scenario):
        result = _run_deterministic_pipeline(clean_scenario)
        assert result.eligibility_passed is True

    def test_no_high_anomalies(self, clean_scenario):
        result = _run_deterministic_pipeline(clean_scenario)
        high = [a for a in result.anomalies if a.severity == "HIGH"]
        assert len(high) == 0

    def test_no_missing_docs(self, clean_scenario):
        missing = find_missing_documents(clean_scenario["documents"])
        assert len(missing) == 0


# ==========================================================================
# Scenario 2: Income Mismatch → REVIEW
# ==========================================================================

class TestIncomeMismatchE2E:
    """End-to-end: Income variance >10% → REVIEW/AMBER."""

    def test_not_green(self, income_mismatch_scenario):
        result = _run_deterministic_pipeline(income_mismatch_scenario)
        assert result.routing_color != "GREEN"

    def test_routing_amber_or_red(self, income_mismatch_scenario):
        result = _run_deterministic_pipeline(income_mismatch_scenario)
        assert result.routing_color in ("AMBER", "RED")

    def test_income_variance_detected(self, income_mismatch_scenario):
        result = _run_deterministic_pipeline(income_mismatch_scenario)
        expected = income_mismatch_scenario["expected_outputs"]
        min_var = expected.get("income_difference_percent_min", 10.0)
        assert result.income_difference_percent >= min_var

    def test_identity_still_matches(self, income_mismatch_scenario):
        result = _run_deterministic_pipeline(income_mismatch_scenario)
        assert result.identity_status == "MATCH"


# ==========================================================================
# Scenario 3: Identity Fraud → REJECT
# ==========================================================================

class TestIdentityFraudE2E:
    """End-to-end: Name & PAN mismatch + forged statement → RED/REJECT."""

    def test_routing_is_red(self, fraud_scenario):
        result = _run_deterministic_pipeline(fraud_scenario)
        assert result.routing_color == "RED"

    def test_recommendation_reject(self, fraud_scenario):
        result = _run_deterministic_pipeline(fraud_scenario)
        assert result.recommendation == "REJECT"

    def test_risk_level_high(self, fraud_scenario):
        result = _run_deterministic_pipeline(fraud_scenario)
        assert result.risk_level == "HIGH"

    def test_identity_mismatch(self, fraud_scenario):
        result = _run_deterministic_pipeline(fraud_scenario)
        assert result.identity_status == "MISMATCH"

    def test_risk_score_below_50(self, fraud_scenario):
        result = _run_deterministic_pipeline(fraud_scenario)
        expected = fraud_scenario["expected_outputs"]
        assert result.risk_score <= expected["risk_score_max"]

    def test_has_high_severity_anomalies(self, fraud_scenario):
        result = _run_deterministic_pipeline(fraud_scenario)
        high = [a for a in result.anomalies if a.severity == "HIGH"]
        assert len(high) >= 1

    def test_statement_arithmetic_invalid(self, fraud_scenario):
        result = _run_deterministic_pipeline(fraud_scenario)
        assert result.statement_arithmetic_status == "MISMATCH"


# ==========================================================================
# Scenario 4: High DTI → REJECT
# ==========================================================================

class TestHighDtiE2E:
    """End-to-end: Overleveraged applicant with high DTI → RED/REJECT."""

    def test_routing_is_red(self, high_dti_scenario):
        result = _run_deterministic_pipeline(high_dti_scenario)
        assert result.routing_color == "RED"

    def test_recommendation_reject(self, high_dti_scenario):
        result = _run_deterministic_pipeline(high_dti_scenario)
        assert result.recommendation == "REJECT"

    def test_dti_above_60(self, high_dti_scenario):
        result = _run_deterministic_pipeline(high_dti_scenario)
        assert result.dti_percent >= 60.0

    def test_eligibility_failed(self, high_dti_scenario):
        result = _run_deterministic_pipeline(high_dti_scenario)
        assert result.eligibility_passed is False


# ==========================================================================
# Scenario 5: Missing Documents → INCOMPLETE
# ==========================================================================

class TestMissingDocsE2E:
    """End-to-end: Missing required documents → INCOMPLETE status."""

    def test_missing_documents_detected(self, missing_docs_scenario):
        missing = find_missing_documents(missing_docs_scenario["documents"])
        expected_missing = missing_docs_scenario["expected_outputs"]["missing_documents"]
        for doc_type in expected_missing:
            assert doc_type in missing

    def test_status_is_incomplete(self, missing_docs_scenario):
        missing = find_missing_documents(missing_docs_scenario["documents"])
        status = "INCOMPLETE" if missing else "EXTRACTED"
        assert status == "INCOMPLETE"


# ==========================================================================
# Scenario 6: Borderline Amber
# ==========================================================================

class TestBorderlineAmberE2E:
    """End-to-end: Moderate risk with employer partial match → AMBER/REVIEW."""

    def test_not_green(self, borderline_scenario):
        result = _run_deterministic_pipeline(borderline_scenario)
        assert result.routing_color != "GREEN"

    def test_routing_amber_or_red(self, borderline_scenario):
        result = _run_deterministic_pipeline(borderline_scenario)
        assert result.routing_color in ("AMBER", "RED")

    def test_identity_matches(self, borderline_scenario):
        result = _run_deterministic_pipeline(borderline_scenario)
        assert result.identity_status == "MATCH"

    def test_has_reviewer_checklist(self, borderline_scenario):
        result = _run_deterministic_pipeline(borderline_scenario)
        assert len(result.reviewer_checklist) >= 1

    def test_has_counterfactual(self, borderline_scenario):
        result = _run_deterministic_pipeline(borderline_scenario)
        assert result.counterfactual_note is not None
        assert len(result.counterfactual_note) > 0
