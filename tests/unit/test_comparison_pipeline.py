"""
Unit Tests: Comparison Pipeline
Tests identity, income, employer, PAN, and liability comparison functions.
Uses golden data fixtures. All deterministic - no LLM calls.

Run:  python -m pytest tests/unit/test_comparison_pipeline.py -v
"""
import pytest
from src.decision_engine.comparison import (
    compare_identity,
    compare_income,
    compare_employer,
    compare_pan,
)
from src.decision_engine.extractors import (
    extract_declared,
    extract_verified,
    extract_liabilities,
    get_doc,
    get_docs,
)
from src.schemas.decision_models import FieldComparison


# ==========================================================================
# 1. Identity Comparison Tests
# ==========================================================================

class TestCompareIdentity:
    """Tests for compare_identity: declared vs verified name + DOB, cross-doc checks."""

    def test_exact_name_match(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        results = compare_identity(declared, verified, all_docs=clean_scenario["documents"])
        # The declared_vs_kyc_name check should MATCH
        kyc_check = [r for r in results if r.field == "declared_vs_kyc_name"]
        assert len(kyc_check) == 1
        assert kyc_check[0].status == "MATCH"

    def test_name_mismatch(self, fraud_scenario):
        declared = fraud_scenario["declared"]
        verified = fraud_scenario["verified"]
        results = compare_identity(declared, verified)
        kyc_check = [r for r in results if r.field == "declared_vs_kyc_name"]
        assert len(kyc_check) == 1
        assert kyc_check[0].status == "MISMATCH"

    def test_dob_match(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        results = compare_identity(declared, verified)
        dob_check = [r for r in results if r.field == "dob"]
        assert len(dob_check) == 1
        assert dob_check[0].status == "MATCH"

    def test_dob_not_available_when_missing(self):
        declared = {"name": "Test User"}
        verified = {"name": "TEST USER"}
        results = compare_identity(declared, verified)
        dob_check = [r for r in results if r.field == "dob"]
        assert len(dob_check) == 1
        assert dob_check[0].status == "NOT_AVAILABLE"

    def test_cross_doc_name_check_payslip(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        results = compare_identity(declared, verified, all_docs=clean_scenario["documents"])
        # Should have cross-document checks for PAYSLIP and BANK_STATEMENT
        cross_checks = [r for r in results if "identity_check_" in r.field]
        assert len(cross_checks) >= 1  # At least payslip check

    def test_cross_doc_name_mismatch(self, fraud_scenario):
        declared = fraud_scenario["declared"]
        verified = fraud_scenario["verified"]
        results = compare_identity(declared, verified, all_docs=fraud_scenario["documents"])
        # Declared name "Rajesh Kumar" vs verified name "RAMESH KUMAR"
        kyc_check = [r for r in results if r.field == "declared_vs_kyc_name"]
        assert kyc_check[0].status == "MISMATCH"

    def test_identity_results_are_field_comparison_models(self, clean_scenario):
        declared = clean_scenario["declared"]
        verified = clean_scenario["verified"]
        results = compare_identity(declared, verified)
        for r in results:
            assert isinstance(r, FieldComparison)
            assert r.comparison_method == "DETERMINISTIC"


# ==========================================================================
# 2. Income Comparison Tests
# ==========================================================================

class TestCompareIncome:
    """Tests for compare_income: declared vs verified net monthly income."""

    def test_income_exact_match(self):
        declared = {"net_monthly": 72000.0}
        verified = {"payslip_net_monthly": 72000.0}
        result = compare_income(declared, verified)
        assert result.status == "MATCH"
        assert result.discrepancy_percent <= 5.0

    def test_income_within_5_percent(self):
        declared = {"net_monthly": 72000.0}
        verified = {"payslip_net_monthly": 70000.0}
        result = compare_income(declared, verified)
        pct = abs(72000 - 70000) / 72000 * 100
        assert result.status == "MATCH" if pct <= 5 else "PARTIAL_MATCH"

    def test_income_partial_match(self):
        declared = {"net_monthly": 80000.0}
        verified = {"payslip_net_monthly": 74000.0}
        result = compare_income(declared, verified)
        pct = abs(80000 - 74000) / 80000 * 100  # 7.5%
        assert result.status == "PARTIAL_MATCH"

    def test_income_mismatch_large_variance(self):
        declared = {"net_monthly": 100000.0}
        verified = {"payslip_net_monthly": 55000.0}
        result = compare_income(declared, verified)
        assert result.status == "MISMATCH"
        assert result.discrepancy_percent > 10.0

    def test_income_zero_declared(self):
        declared = {"net_monthly": 0.0}
        verified = {"payslip_net_monthly": 72000.0}
        result = compare_income(declared, verified)
        assert result.status == "NOT_AVAILABLE"

    def test_income_zero_verified(self):
        declared = {"net_monthly": 72000.0}
        verified = {"payslip_net_monthly": 0.0}
        result = compare_income(declared, verified)
        assert result.status == "NOT_AVAILABLE"

    def test_income_both_zero(self):
        declared = {"net_monthly": 0.0}
        verified = {"payslip_net_monthly": 0.0}
        result = compare_income(declared, verified)
        assert result.status == "NOT_AVAILABLE"

    def test_income_golden_clean(self, clean_scenario):
        result = compare_income(clean_scenario["declared"], clean_scenario["verified"])
        assert result.status == "MATCH"

    def test_income_golden_mismatch(self, income_mismatch_scenario):
        result = compare_income(
            income_mismatch_scenario["declared"],
            income_mismatch_scenario["verified"]
        )
        assert result.status in ("PARTIAL_MATCH", "MISMATCH")


# ==========================================================================
# 3. Employer Comparison Tests
# ==========================================================================

class TestCompareEmployer:
    """Tests for compare_employer: declared vs verified employer name."""

    def test_exact_match(self):
        declared = {"employer": "Infosys Ltd"}
        verified = {"employer": "Infosys Ltd"}
        result = compare_employer(declared, verified)
        assert result.status == "MATCH"

    def test_partial_match_substring(self):
        declared = {"employer": "Cognizant Technology Solutions"}
        verified = {"employer": "Cognizant"}
        result = compare_employer(declared, verified)
        assert result.status == "PARTIAL_MATCH"

    def test_mismatch(self):
        declared = {"employer": "Infosys Ltd"}
        verified = {"employer": "TCS Limited"}
        result = compare_employer(declared, verified)
        assert result.status == "MISMATCH"

    def test_not_available_when_missing(self):
        declared = {"employer": None}
        verified = {"employer": "Infosys Ltd"}
        result = compare_employer(declared, verified)
        assert result.status == "NOT_AVAILABLE"

    def test_not_available_both_missing(self):
        declared = {}
        verified = {}
        result = compare_employer(declared, verified)
        assert result.status == "NOT_AVAILABLE"

    def test_case_insensitive_comparison(self):
        declared = {"employer": "INFOSYS LTD"}
        verified = {"employer": "infosys ltd"}
        result = compare_employer(declared, verified)
        assert result.status == "MATCH"


# ==========================================================================
# 4. PAN Comparison Tests
# ==========================================================================

class TestComparePan:
    """Tests for compare_pan: declared vs verified PAN number."""

    def test_exact_match(self):
        declared = {"pan_number": "AVIBH2505F"}
        verified = {"pan_number": "AVIBH2505F"}
        result = compare_pan(declared, verified)
        assert result.status == "MATCH"

    def test_match_case_insensitive(self):
        declared = {"pan_number": "avibh2505f"}
        verified = {"pan_number": "AVIBH2505F"}
        result = compare_pan(declared, verified)
        assert result.status == "MATCH"

    def test_mismatch(self):
        declared = {"pan_number": "RAJKK1011F"}
        verified = {"pan_number": "RAMKK1011F"}
        result = compare_pan(declared, verified)
        assert result.status == "MISMATCH"

    def test_not_available_declared_missing(self):
        declared = {}
        verified = {"pan_number": "AVIBH2505F"}
        result = compare_pan(declared, verified)
        assert result.status == "NOT_AVAILABLE"

    def test_not_available_verified_missing(self):
        declared = {"pan_number": "AVIBH2505F"}
        verified = {}
        result = compare_pan(declared, verified)
        assert result.status == "NOT_AVAILABLE"

    def test_pan_alt_key(self):
        """Should also check 'pan' key as fallback."""
        declared = {"pan": "AVIBH2505F"}
        verified = {"pan_number": "AVIBH2505F"}
        result = compare_pan(declared, verified)
        assert result.status == "MATCH"

    def test_golden_clean_match(self, clean_scenario):
        result = compare_pan(clean_scenario["declared"], clean_scenario["verified"])
        assert result.status == "MATCH"

    def test_golden_fraud_mismatch(self, fraud_scenario):
        result = compare_pan(fraud_scenario["declared"], fraud_scenario["verified"])
        assert result.status == "MISMATCH"


# ==========================================================================
# 5. Extractor Tests (extract_declared, extract_verified, extract_liabilities)
# ==========================================================================

class TestExtractDeclared:
    """Tests for extract_declared: pulls data from LOAN_APPLICATION doc."""

    def test_extracts_name(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        result = extract_declared(payload)
        assert result["name"] == "Avinash Bhatt"

    def test_extracts_pan(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        result = extract_declared(payload)
        assert result["pan_number"] == "AVIBH2505F"

    def test_extracts_employer(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        result = extract_declared(payload)
        assert result["employer"] == "Infosys Ltd"

    def test_uses_financials_fallback(self):
        payload = {
            "documents": [],
            "financials": {"loan_request": {"declared_net_monthly": 72000.0, "requested_amount": 300000.0}}
        }
        result = extract_declared(payload)
        assert result["net_monthly"] == 72000.0
        assert result["loan_amount_requested"] == 300000.0

    def test_empty_payload(self):
        result = extract_declared({"documents": []})
        assert result["name"] is None


class TestExtractVerified:
    """Tests for extract_verified: aggregates from PAN, Aadhaar, Payslip, Form16, Bank."""

    def test_extracts_pan_name(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        result = extract_verified(payload)
        assert result["name"] == "AVINASH BHATT"

    def test_extracts_payslip_net(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        result = extract_verified(payload)
        assert result["payslip_net_monthly"] == 72000.0

    def test_extracts_employer_from_payslip(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        result = extract_verified(payload)
        assert result["employer"] == "Infosys Ltd"


class TestExtractLiabilities:
    """Tests for extract_liabilities: pulls from loan app + bank transactions."""

    def test_no_liabilities(self, clean_scenario):
        payload = {"documents": clean_scenario["documents"]}
        result = extract_liabilities(payload)
        assert result["detected_emi"] == 0.0

    def test_with_emi_transactions(self):
        payload = {
            "documents": [
                {
                    "doc_type": "BANK_STATEMENT",
                    "extracted_data": {
                        "transactions": [
                            {"narration": "HOME LOAN EMI-SBI", "amount": -15000.0, "category": "emi_debit"},
                            {"narration": "CAR LOAN-HDFC", "amount": -8000.0, "category": "emi_debit"},
                        ]
                    }
                }
            ]
        }
        result = extract_liabilities(payload)
        assert result["detected_emi"] > 0

    def test_declared_total_emi_fallback(self):
        payload = {
            "documents": [
                {
                    "doc_type": "LOAN_APPLICATION",
                    "extracted_data": {"declared_total_emi": 12000.0}
                }
            ]
        }
        result = extract_liabilities(payload)
        assert len(result["declared_liabilities"]) == 1
        assert result["declared_liabilities"][0]["monthly_emi"] == 12000.0


class TestGetDoc:
    """Tests for get_doc helper function."""

    def test_finds_by_doc_type(self):
        payload = {"documents": [
            {"doc_type": "PAN_CARD", "extracted_data": {"pan_number": "XYZ"}},
            {"doc_type": "PAYSLIP", "extracted_data": {"net_pay": 50000}},
        ]}
        result = get_doc(payload, "PAN_CARD")
        assert result["pan_number"] == "XYZ"

    def test_returns_empty_when_not_found(self):
        payload = {"documents": [{"doc_type": "PAYSLIP", "extracted_data": {}}]}
        result = get_doc(payload, "PAN_CARD")
        assert result == {}

    def test_finds_by_document_type_key(self):
        payload = {"documents": [
            {"document_type": "BANK_STATEMENT", "extracted_data": {"opening_balance": 100000}},
        ]}
        result = get_doc(payload, "BANK_STATEMENT")
        assert result["opening_balance"] == 100000


class TestGetDocs:
    """Tests for get_docs: returns list of all matching doc type."""

    def test_multiple_payslips(self):
        payload = {"documents": [
            {"doc_type": "PAYSLIP", "extracted_data": {"net_pay": 70000}},
            {"doc_type": "PAYSLIP", "extracted_data": {"net_pay": 72000}},
        ]}
        result = get_docs(payload, "PAYSLIP")
        assert len(result) == 2

    def test_no_matches(self):
        payload = {"documents": [{"doc_type": "PAYSLIP", "extracted_data": {}}]}
        result = get_docs(payload, "FORM_16_OR_ITR")
        assert result == []
