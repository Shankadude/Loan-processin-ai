"""
Integration Tests: Pipeline Chaining
Tests that the output of each pipeline stage correctly feeds into the next stage.
Validates the data contracts between:
  - Extractors → Comparison Engine
  - Comparison Engine → Risk Scorer (score_application)
  - Risk Scorer → DecisionResult model

These tests use golden data and do NOT call LLM/Vision APIs.

Run:  python -m pytest tests/integration/test_pipeline_chaining.py -v
"""
import pytest
from src.decision_engine.extractors import extract_declared, extract_verified, extract_liabilities
from src.decision_engine.comparison import compare_identity, compare_income, compare_employer, compare_pan
from src.decision_engine.risk_scorer import score_application
from src.decision_engine.calculations import (
    calculate_income_metrics,
    calculate_obligation_metrics,
    validate_statement_arithmetic,
    check_eligibility,
)
from src.schemas.decision_models import DecisionResult, FieldComparison


# ==========================================================================
# 1. Extractor → Comparison Chaining
# ==========================================================================

class TestExtractorToComparison:
    """Tests that extractor outputs are compatible with comparison function inputs."""

    def test_declared_feeds_compare_identity(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        declared = extract_declared(payload)
        verified = extract_verified(payload)

        # Should not raise
        results = compare_identity(declared, verified, all_docs=clean_scenario["documents"])
        assert len(results) >= 1
        for r in results:
            assert isinstance(r, FieldComparison)

    def test_declared_feeds_compare_income(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        declared = extract_declared(payload)
        verified = extract_verified(payload)

        result = compare_income(declared, verified)
        assert isinstance(result, FieldComparison)
        assert result.field == "net_monthly_income"

    def test_declared_feeds_compare_employer(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        declared = extract_declared(payload)
        verified = extract_verified(payload)

        result = compare_employer(declared, verified)
        assert isinstance(result, FieldComparison)
        assert result.field == "employer"

    def test_declared_feeds_compare_pan(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        declared = extract_declared(payload)
        verified = extract_verified(payload)

        result = compare_pan(declared, verified)
        assert isinstance(result, FieldComparison)
        assert result.field == "pan_number"

    def test_extractor_output_keys_match_comparison_expectations(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        declared = extract_declared(payload)
        verified = extract_verified(payload)

        # compare_identity expects: declared["name"], declared["dob"], verified["name"], verified["dob"]
        assert "name" in declared
        assert "dob" in declared
        assert "name" in verified

        # compare_income expects: declared["net_monthly"], verified["payslip_net_monthly"]
        assert "net_monthly" in declared
        assert "payslip_net_monthly" in verified

        # compare_employer expects: declared["employer"], verified["employer"]
        assert "employer" in declared
        assert "employer" in verified

        # compare_pan expects: declared["pan_number"], verified["pan_number"]
        assert "pan_number" in declared
        assert "pan_number" in verified


# ==========================================================================
# 2. Comparison → Risk Scorer Chaining
# ==========================================================================

class TestComparisonToRiskScorer:
    """Tests that comparison outputs feed correctly into score_application."""

    def test_full_chain_clean(self, clean_scenario):
        payload = {
            "documents": clean_scenario["documents"],
            "financials": {"loan_request": {
                "declared_net_monthly": clean_scenario["declared"]["net_monthly"],
                "requested_amount": clean_scenario["declared"]["loan_amount_requested"],
            }}
        }
        declared = extract_declared(payload)
        verified = extract_verified(payload)
        liabilities = extract_liabilities(payload)

        comparisons = compare_identity(declared, verified, all_docs=clean_scenario["documents"])
        comparisons.append(compare_pan(declared, verified))
        comparisons.append(compare_income(declared, verified))
        comparisons.append(compare_employer(declared, verified))

        # score_application should accept this chain output without error
        result = score_application(
            application_id="CHAIN-CLEAN-001",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=liabilities,
            comparisons=comparisons,
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=declared.get("loan_amount_requested", 0),
        )

        assert isinstance(result, DecisionResult)
        assert result.application_id == "CHAIN-CLEAN-001"

    def test_full_chain_fraud(self, fraud_scenario):
        payload = {"documents": fraud_scenario["documents"]}
        declared = extract_declared(payload)
        verified = extract_verified(payload)
        liabilities = extract_liabilities(payload)

        comparisons = compare_identity(declared, verified, all_docs=fraud_scenario["documents"])
        comparisons.append(compare_pan(declared, verified))
        comparisons.append(compare_income(declared, verified))
        comparisons.append(compare_employer(declared, verified))

        result = score_application(
            application_id="CHAIN-FRAUD-001",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=liabilities,
            comparisons=comparisons,
            bank_statement_data=fraud_scenario["bank_statement"],
            requested_amount=fraud_scenario["declared"].get("loan_amount_requested", 0),
        )

        assert isinstance(result, DecisionResult)
        assert result.routing_color == "RED"


# ==========================================================================
# 3. Calculations → Risk Scorer Chaining
# ==========================================================================

class TestCalculationsToRiskScorer:
    """Tests that calculation functions chain correctly within score_application."""

    def test_income_metrics_chain(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]

        income_calc = calculate_income_metrics(
            declared_net=float(declared.get("net_monthly", 0)),
            verified_net=float(verified.get("payslip_net_monthly", 0)),
            bank_avg_credit=float(verified.get("bank_avg_salary_credit", 0)),
        )

        # Output should have all keys that obligation_metrics and risk_scorer expect
        assert "effective_verified_income" in income_calc
        assert "income_difference_percent" in income_calc
        assert income_calc["effective_verified_income"] > 0

    def test_obligation_metrics_chain(self, clean_scenario):
        verified = clean_scenario["verified"]
        liabilities = clean_scenario["liabilities"]

        income_calc = calculate_income_metrics(
            declared_net=float(clean_scenario["declared"].get("net_monthly", 0)),
            verified_net=float(verified.get("payslip_net_monthly", 0)),
        )

        obligation_calc = calculate_obligation_metrics(
            detected_emi=float(liabilities.get("detected_emi", 0)),
            declared_liabilities=liabilities.get("declared_liabilities", []),
            verified_monthly_net=income_calc["effective_verified_income"],
            proposed_emi=round(clean_scenario["declared"]["loan_amount_requested"] * 0.025, 2),
        )

        assert "foir_percentage" in obligation_calc
        assert "dti_percent" in obligation_calc
        assert "has_undisclosed_liabilities" in obligation_calc
        assert "total_monthly_obligations" in obligation_calc

    def test_statement_to_eligibility_chain(self, clean_scenario):
        bs = clean_scenario["bank_statement"]
        statement_calc = validate_statement_arithmetic(
            opening_balance=bs["opening_balance"],
            total_credits=bs["total_credits"],
            total_debits=bs["total_debits"],
            closing_balance=bs["closing_balance"],
        )

        income_calc = calculate_income_metrics(
            declared_net=float(clean_scenario["declared"]["net_monthly"]),
            verified_net=float(clean_scenario["verified"]["payslip_net_monthly"]),
        )

        obligation_calc = calculate_obligation_metrics(
            detected_emi=0.0,
            verified_monthly_net=income_calc["effective_verified_income"],
        )

        eligibility_calc = check_eligibility(
            verified_income=income_calc["effective_verified_income"],
            foir_percentage=obligation_calc["foir_percentage"],
            income_variance_percent=income_calc["income_difference_percent"],
        )

        assert "passed" in eligibility_calc
        assert "status" in eligibility_calc


# ==========================================================================
# 4. DecisionResult → Serialization Chain
# ==========================================================================

class TestDecisionResultSerialization:
    """Tests that DecisionResult can be serialized for MongoDB storage and API response."""

    def test_model_dump_is_json_safe(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        declared = extract_declared(payload)
        verified = extract_verified(payload)
        liabilities = extract_liabilities(payload)

        comparisons = compare_identity(declared, verified)
        comparisons.append(compare_pan(declared, verified))
        comparisons.append(compare_income(declared, verified))
        comparisons.append(compare_employer(declared, verified))

        result = score_application(
            application_id="SERIAL-001",
            declared_payload=declared,
            verified_payload=verified,
            liabilities_payload=liabilities,
            comparisons=comparisons,
            bank_statement_data=clean_scenario["bank_statement"],
            requested_amount=300000.0,
        )

        data = result.model_dump()

        # Check key fields are present
        assert isinstance(data, dict)
        assert isinstance(data.get("anomalies"), list)
        assert isinstance(data.get("discrepancies"), list)
        assert isinstance(data.get("risk_factors"), list)
        assert isinstance(data.get("reviewer_checklist"), list)

        # Nested step payloads
        assert isinstance(data.get("step4_comparison"), dict)
        assert isinstance(data.get("step5_calculation"), dict)
        assert isinstance(data.get("step6_risk_anomaly"), dict)
