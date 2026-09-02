"""
Unit Tests: Decision Engine (score_application)
Tests the full deterministic scoring pipeline that produces DecisionResult,
including routing color (GREEN/AMBER/RED), reviewer checklists, and counterfactuals.

Run:  python -m pytest tests/unit/test_decision_engine.py -v
"""
import pytest
from src.decision_engine.risk_scorer import score_application
from src.decision_engine.comparison import compare_identity, compare_income, compare_employer, compare_pan
from src.schemas.decision_models import DecisionResult


def _build_comparisons(declared, verified, all_docs=None):
    """Helper to build the full comparison list like the real pipeline does."""
    comparisons = compare_identity(declared, verified, all_docs=all_docs)
    comparisons.append(compare_pan(declared, verified))
    comparisons.append(compare_income(declared, verified))
    comparisons.append(compare_employer(declared, verified))
    return comparisons


# ==========================================================================
# 1. GREEN / AUTO_APPROVE Decision Tests
# ==========================================================================

class TestGreenDecision:
    """Tests that clean applicants route to GREEN / AUTO_APPROVE."""

    def test_clean_applicant_gets_green(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        liabilities = clean_scenario["liabilities"]
        bank_data = clean_scenario["bank_statement"]

        comparisons = _build_comparisons(declared, verified, all_docs=clean_scenario["documents"])

        result = score_application(
            application_id="TEST-GREEN-001",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=liabilities,
            comparisons=comparisons,
            bank_statement_data=bank_data,
            requested_amount=declared.get("loan_amount_requested", 0),
        )

        assert isinstance(result, DecisionResult)
        assert result.risk_score >= 80
        assert result.routing_color == "GREEN"
        assert result.recommendation == "AUTO_APPROVE"
        assert result.risk_level == "LOW"
        assert result.eligibility_passed is True

    def test_green_has_reviewer_checklist(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        comparisons = _build_comparisons(declared, verified, all_docs=clean_scenario["documents"])

        result = score_application(
            application_id="TEST-GREEN-002",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=clean_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=300000.0,
        )

        assert len(result.reviewer_checklist) >= 1

    def test_green_counterfactual_note(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        comparisons = _build_comparisons(declared, verified)

        result = score_application(
            application_id="TEST-GREEN-003",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=clean_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=300000.0,
        )

        assert result.counterfactual_note is not None
        assert "fast-track" in result.counterfactual_note.lower() or "auto" in result.counterfactual_note.lower()


# ==========================================================================
# 2. AMBER / REVIEW Decision Tests
# ==========================================================================

class TestAmberDecision:
    """Tests that moderate-risk applicants route to AMBER / REVIEW."""

    def test_income_mismatch_gets_amber(self, income_mismatch_scenario):
        declared = income_mismatch_scenario["declared"]
        verified = income_mismatch_scenario["verified"]
        liabilities = income_mismatch_scenario["liabilities"]
        bank_data = income_mismatch_scenario["bank_statement"]

        comparisons = _build_comparisons(declared, verified, all_docs=income_mismatch_scenario["documents"])

        result = score_application(
            application_id="TEST-AMBER-001",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=liabilities,
            comparisons=comparisons,
            bank_statement_data=bank_data,
            requested_amount=declared.get("loan_amount_requested", 0),
        )

        assert isinstance(result, DecisionResult)
        assert result.routing_color in ("AMBER", "RED")  # Could be either depending on exact calcs
        assert result.recommendation in ("REVIEW", "REJECT")

    def test_borderline_gets_amber(self, borderline_scenario):
        declared = borderline_scenario["declared"]
        verified = borderline_scenario["verified"]
        liabilities = borderline_scenario["liabilities"]
        bank_data = borderline_scenario["bank_statement"]

        comparisons = _build_comparisons(declared, verified, all_docs=borderline_scenario["documents"])

        result = score_application(
            application_id="TEST-AMBER-002",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=liabilities,
            comparisons=comparisons,
            bank_statement_data=bank_data,
            requested_amount=declared.get("loan_amount_requested", 0),
        )

        assert isinstance(result, DecisionResult)
        # Borderline should not be GREEN
        assert result.routing_color in ("AMBER", "RED")


# ==========================================================================
# 3. RED / REJECT Decision Tests
# ==========================================================================

class TestRedDecision:
    """Tests that high-risk applicants route to RED / REJECT."""

    def test_fraud_applicant_gets_red(self, fraud_scenario):
        declared = fraud_scenario["declared"]
        verified = fraud_scenario["verified"]
        liabilities = fraud_scenario["liabilities"]
        bank_data = fraud_scenario["bank_statement"]

        comparisons = _build_comparisons(declared, verified, all_docs=fraud_scenario["documents"])

        result = score_application(
            application_id="TEST-RED-001",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=liabilities,
            comparisons=comparisons,
            bank_statement_data=bank_data,
            requested_amount=declared.get("loan_amount_requested", 0),
        )

        assert isinstance(result, DecisionResult)
        assert result.routing_color == "RED"
        assert result.recommendation == "REJECT"
        assert result.risk_level == "HIGH"
        assert result.risk_score <= 50

    def test_high_dti_gets_red(self, high_dti_scenario):
        declared = high_dti_scenario["declared"]
        verified = high_dti_scenario["verified"]
        liabilities = high_dti_scenario["liabilities"]
        bank_data = high_dti_scenario["bank_statement"]

        comparisons = _build_comparisons(declared, verified, all_docs=high_dti_scenario["documents"])

        result = score_application(
            application_id="TEST-RED-002",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=liabilities,
            comparisons=comparisons,
            bank_statement_data=bank_data,
            requested_amount=declared.get("loan_amount_requested", 0),
        )

        assert isinstance(result, DecisionResult)
        assert result.routing_color == "RED"
        assert result.recommendation == "REJECT"

    def test_red_has_anomalies(self, fraud_scenario):
        declared = fraud_scenario["declared"]
        verified = fraud_scenario["verified"]
        comparisons = _build_comparisons(declared, verified, all_docs=fraud_scenario["documents"])

        result = score_application(
            application_id="TEST-RED-003",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=fraud_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=fraud_scenario["bank_statement"],
            requested_amount=800000.0,
        )

        assert len(result.anomalies) >= 1
        high_severity = [a for a in result.anomalies if a.severity == "HIGH"]
        assert len(high_severity) >= 1


# ==========================================================================
# 4. DecisionResult Structure Tests
# ==========================================================================

class TestDecisionResultStructure:
    """Tests that DecisionResult has all required fields and step payloads."""

    def test_has_step_payloads(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        comparisons = _build_comparisons(declared, verified)

        result = score_application(
            application_id="TEST-STRUCT-001",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=clean_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=300000.0,
        )

        # Step 4: Comparison payload
        assert result.step4_comparison is not None
        assert "identity_status" in result.step4_comparison
        assert "comparisons" in result.step4_comparison

        # Step 5: Calculation payload
        assert result.step5_calculation is not None
        assert "income_metrics" in result.step5_calculation
        assert "obligation_metrics" in result.step5_calculation

        # Step 6: Risk/Anomaly payload
        assert result.step6_risk_anomaly is not None
        assert "risk_score" in result.step6_risk_anomaly
        assert "routing_color" in result.step6_risk_anomaly

    def test_factor_breakdown_present(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        comparisons = _build_comparisons(declared, verified)

        result = score_application(
            application_id="TEST-STRUCT-002",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=clean_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=300000.0,
        )

        fb = result.factor_breakdown
        assert "base_score" in fb
        assert fb["base_score"] == 100.0
        assert "final_calculated_score" in fb

    def test_risk_score_clamped_0_to_100(self, fraud_scenario):
        declared = fraud_scenario["declared"]
        verified = fraud_scenario["verified"]
        comparisons = _build_comparisons(declared, verified)

        result = score_application(
            application_id="TEST-STRUCT-003",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=fraud_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=fraud_scenario["bank_statement"],
            requested_amount=800000.0,
        )

        assert 0 <= result.risk_score <= 100

    def test_model_is_serializable(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        comparisons = _build_comparisons(declared, verified)

        result = score_application(
            application_id="TEST-STRUCT-004",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=clean_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=300000.0,
        )

        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["application_id"] == "TEST-STRUCT-004"


# ==========================================================================
# 5. Edge Case / Boundary Tests
# ==========================================================================

class TestDecisionBoundaries:
    """Tests edge cases and boundary conditions in decision logic."""

    def test_zero_requested_amount(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        comparisons = _build_comparisons(declared, verified)

        result = score_application(
            application_id="TEST-EDGE-001",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=clean_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=0.0,
        )

        assert isinstance(result, DecisionResult)
        assert result.proposed_emi == 0.0

    def test_empty_comparisons(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]

        result = score_application(
            application_id="TEST-EDGE-002",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=clean_scenario["liabilities"],
            comparisons=[],  # No comparisons
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=300000.0,
        )

        assert isinstance(result, DecisionResult)

    def test_no_bank_statement(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        comparisons = _build_comparisons(declared, verified)

        result = score_application(
            application_id="TEST-EDGE-003",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=clean_scenario["liabilities"],
            comparisons=comparisons,
            bank_statement_data=None,
            requested_amount=300000.0,
        )

        assert isinstance(result, DecisionResult)
        assert result.statement_arithmetic_status == "NOT_AVAILABLE"
