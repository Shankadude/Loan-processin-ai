"""
Unit Tests: Risk Engine
Tests FOIR calculation, risk scoring, anomaly detection, boundary conditions,
statement arithmetic validation, and eligibility checks.

Run:  python -m pytest tests/unit/test_risk_engine.py -v
"""
import pytest
from src.decision_engine.calculations import (
    calculate_income_metrics,
    calculate_obligation_metrics,
    validate_statement_arithmetic,
    check_eligibility,
    calculate_statement_metrics,
)
from src.decision_engine.discrepancy import detect_discrepancies
from src.decision_engine.comparison import compare_identity, compare_income, compare_employer, compare_pan
from src.schemas.decision_models import FieldComparison, Anomaly


# ==========================================================================
# 1. Income Metric Calculation Tests
# ==========================================================================

class TestCalculateIncomeMetrics:
    """Tests for calculate_income_metrics: income variance computation."""

    def test_exact_match_income(self):
        result = calculate_income_metrics(declared_net=72000.0, verified_net=72000.0)
        assert result["income_difference"] == 0.0
        assert result["income_difference_percent"] == 0.0
        assert result["effective_verified_income"] == 72000.0

    def test_conservative_min_pick(self):
        """When both verified and bank are present, picks the smaller."""
        result = calculate_income_metrics(
            declared_net=80000.0, verified_net=72000.0, bank_avg_credit=68000.0
        )
        assert result["effective_verified_income"] == 68000.0

    def test_only_verified_net(self):
        result = calculate_income_metrics(declared_net=80000.0, verified_net=72000.0, bank_avg_credit=0.0)
        assert result["effective_verified_income"] == 72000.0

    def test_only_bank_credit(self):
        result = calculate_income_metrics(declared_net=80000.0, verified_net=0.0, bank_avg_credit=68000.0)
        assert result["effective_verified_income"] == 68000.0

    def test_fallback_to_declared(self):
        result = calculate_income_metrics(declared_net=80000.0, verified_net=0.0, bank_avg_credit=0.0)
        assert result["effective_verified_income"] == 80000.0

    def test_variance_calculation(self):
        result = calculate_income_metrics(declared_net=100000.0, verified_net=85000.0)
        assert result["income_difference"] == 15000.0
        assert result["income_difference_percent"] == 15.0

    def test_zero_declared_zero_percent(self):
        result = calculate_income_metrics(declared_net=0.0, verified_net=50000.0)
        assert result["income_difference_percent"] == 0.0

    def test_none_values_coerced(self):
        result = calculate_income_metrics(declared_net=None, verified_net=None)
        assert result["declared_monthly_net"] == 0.0
        assert result["verified_monthly_net"] == 0.0

    def test_payslip_average(self):
        """Payslip objects should override verified_net with their average."""
        payslips = [
            {"extracted_data": {"net_pay": 70000}},
            {"extracted_data": {"net_pay": 74000}},
        ]
        result = calculate_income_metrics(declared_net=72000.0, verified_net=0.0, payslips=payslips)
        assert result["verified_monthly_net"] == 72000.0  # avg of 70k and 74k

    def test_bank_transaction_salary_credits(self):
        txns = [
            {"category": "salary_credit", "amount": 71000.0},
            {"category": "salary_credit", "amount": 73000.0},
        ]
        result = calculate_income_metrics(
            declared_net=72000.0, verified_net=72000.0,
            bank_transactions=txns
        )
        assert result["bank_avg_salary_credit"] == 72000.0


# ==========================================================================
# 2. Obligation / FOIR Metric Tests
# ==========================================================================

class TestCalculateObligationMetrics:
    """Tests for calculate_obligation_metrics: DTI/FOIR, undisclosed liabilities."""

    def test_zero_obligations(self):
        result = calculate_obligation_metrics(
            detected_emi=0.0,
            declared_liabilities=[],
            verified_monthly_net=72000.0,
        )
        assert result["foir_percentage"] == 0.0
        assert result["dti_status"] == "LOW"
        assert result["has_undisclosed_liabilities"] is False

    def test_low_dti(self):
        result = calculate_obligation_metrics(
            detected_emi=5000.0,
            declared_liabilities=[{"emi_amount": 5000.0}],
            verified_monthly_net=72000.0,
        )
        assert result["dti_percent"] < 30.0
        assert result["dti_status"] == "LOW"

    def test_moderate_dti(self):
        result = calculate_obligation_metrics(
            detected_emi=20000.0,
            declared_liabilities=[{"emi_amount": 20000.0}],
            verified_monthly_net=50000.0,
            proposed_emi=5000.0,
        )
        # (20000 + 5000) / 50000 = 50%
        assert result["dti_percent"] == 50.0
        assert result["dti_status"] in ("MODERATE", "HIGH")

    def test_high_dti(self):
        result = calculate_obligation_metrics(
            detected_emi=30000.0,
            declared_liabilities=[{"emi_amount": 25000.0}],
            verified_monthly_net=48500.0,
            proposed_emi=15000.0,
        )
        # total = 30000 + 15000 = 45000, DTI = 45000/48500 = ~92.8%
        assert result["dti_percent"] > 50.0
        assert result["dti_status"] == "HIGH"

    def test_undisclosed_liabilities_detected(self):
        result = calculate_obligation_metrics(
            detected_emi=15000.0,
            declared_liabilities=[{"emi_amount": 5000.0}],
            verified_monthly_net=72000.0,
        )
        # gap = 15000 - 5000 = 10000, threshold = 2000
        assert result["has_undisclosed_liabilities"] is True
        assert result["undisclosed_liability_gap"] == 10000.0

    def test_no_undisclosed_small_gap(self):
        result = calculate_obligation_metrics(
            detected_emi=6000.0,
            declared_liabilities=[{"emi_amount": 5000.0}],
            verified_monthly_net=72000.0,
        )
        # gap = 1000, under 2000 threshold
        assert result["has_undisclosed_liabilities"] is False

    def test_proposed_emi_added(self):
        result = calculate_obligation_metrics(
            detected_emi=0.0,
            declared_liabilities=[],
            verified_monthly_net=72000.0,
            proposed_emi=7500.0,
        )
        assert result["proposed_emi"] == 7500.0
        assert result["total_monthly_obligations"] == 7500.0

    def test_disposable_income_never_negative(self):
        result = calculate_obligation_metrics(
            detected_emi=80000.0,
            declared_liabilities=[],
            verified_monthly_net=50000.0,
            proposed_emi=10000.0,
        )
        assert result["disposable_income"] >= 0.0

    def test_zero_income_zero_dti(self):
        result = calculate_obligation_metrics(
            detected_emi=10000.0,
            verified_monthly_net=0.0,
        )
        assert result["dti_percent"] == 0.0


# ==========================================================================
# 3. Statement Arithmetic Validation Tests
# ==========================================================================

class TestValidateStatementArithmetic:
    """Tests for validate_statement_arithmetic: detects forged bank statements."""

    def test_balanced_statement(self):
        result = validate_statement_arithmetic(
            opening_balance=125000.0,
            total_credits=215000.0,
            total_debits=180000.0,
            closing_balance=160000.0,
        )
        assert result["is_valid"] is True
        assert result["status"] == "MATCH"

    def test_tampered_statement(self):
        # Expected closing = 125000 + 215000 - 180000 = 160000, but stated is 185000
        result = validate_statement_arithmetic(
            opening_balance=125000.0,
            total_credits=215000.0,
            total_debits=180000.0,
            closing_balance=185000.0,
        )
        assert result["is_valid"] is False
        assert result["status"] == "MISMATCH"
        assert result["difference_amount"] == 25000.0

    def test_within_tolerance(self):
        # Expected = 160000, stated = 160003 (diff = 3, < max_error 5)
        result = validate_statement_arithmetic(
            opening_balance=125000.0,
            total_credits=215000.0,
            total_debits=180000.0,
            closing_balance=160003.0,
        )
        assert result["is_valid"] is True
        assert result["status"] == "MATCH"

    def test_exactly_at_tolerance(self):
        result = validate_statement_arithmetic(
            opening_balance=100000.0,
            total_credits=50000.0,
            total_debits=30000.0,
            closing_balance=120005.0,  # expected = 120000, diff = 5
        )
        assert result["is_valid"] is True

    def test_missing_fields(self):
        result = validate_statement_arithmetic(
            opening_balance=125000.0,
            total_credits=None,
            total_debits=180000.0,
            closing_balance=160000.0,
        )
        assert result["is_valid"] is True
        assert result["status"] == "NOT_AVAILABLE"

    def test_all_none(self):
        result = validate_statement_arithmetic()
        assert result["status"] == "NOT_AVAILABLE"

    def test_custom_max_error(self):
        result = validate_statement_arithmetic(
            opening_balance=100000.0,
            total_credits=50000.0,
            total_debits=30000.0,
            closing_balance=120100.0,  # expected = 120000, diff = 100
            max_error=200.0,
        )
        assert result["is_valid"] is True

    def test_golden_clean_statement(self, clean_scenario):
        bs = clean_scenario["bank_statement"]
        result = validate_statement_arithmetic(
            opening_balance=bs["opening_balance"],
            total_credits=bs["total_credits"],
            total_debits=bs["total_debits"],
            closing_balance=bs["closing_balance"],
        )
        assert result["is_valid"] is True

    def test_golden_fraud_statement(self, fraud_scenario):
        bs = fraud_scenario["bank_statement"]
        result = validate_statement_arithmetic(
            opening_balance=bs["opening_balance"],
            total_credits=bs["total_credits"],
            total_debits=bs["total_debits"],
            closing_balance=bs["closing_balance"],
        )
        # 50000 + 180000 - 160000 = 70000 != 85000 => MISMATCH
        assert result["is_valid"] is False


# ==========================================================================
# 4. Eligibility Check Tests
# ==========================================================================

class TestCheckEligibility:
    """Tests for check_eligibility: policy-based underwriting checks."""

    def test_all_pass(self):
        result = check_eligibility(
            verified_income=72000.0,
            foir_percentage=15.0,
            income_variance_percent=3.0,
        )
        assert result["passed"] is True
        assert result["status"] == "PASS"

    def test_income_below_minimum(self):
        result = check_eligibility(
            verified_income=20000.0,  # below 25000 minimum
            foir_percentage=15.0,
            income_variance_percent=3.0,
        )
        assert result["passed"] is False
        assert any("below policy minimum" in r for r in result["reasons"])

    def test_foir_exceeds_threshold(self):
        result = check_eligibility(
            verified_income=72000.0,
            foir_percentage=55.0,  # exceeds 50% threshold
            income_variance_percent=3.0,
        )
        assert result["passed"] is False
        assert any("FOIR" in r or "DTI" in r for r in result["reasons"])

    def test_income_variance_exceeds(self):
        result = check_eligibility(
            verified_income=72000.0,
            foir_percentage=15.0,
            income_variance_percent=15.0,  # exceeds 10% tolerance
        )
        assert result["passed"] is False
        assert any("variance" in r.lower() for r in result["reasons"])

    def test_undisclosed_gap_exceeds(self):
        result = check_eligibility(
            verified_income=72000.0,
            foir_percentage=15.0,
            income_variance_percent=3.0,
            undisclosed_liability_gap=5000.0,  # exceeds 2000 limit
        )
        assert result["passed"] is False
        assert any("undisclosed" in r.lower() for r in result["reasons"])

    def test_multiple_failures(self):
        result = check_eligibility(
            verified_income=20000.0,
            foir_percentage=55.0,
            income_variance_percent=15.0,
            undisclosed_liability_gap=5000.0,
        )
        assert result["passed"] is False
        assert len(result["reasons"]) >= 3


# ==========================================================================
# 5. Statement Metrics Tests
# ==========================================================================

class TestCalculateStatementMetrics:
    """Tests for calculate_statement_metrics: salary-to-EMI ratio."""

    def test_basic_ratio(self):
        result = calculate_statement_metrics(bank_avg_credit=72000.0, detected_emi=18000.0)
        assert result["salary_to_emi_percent"] == 25.0
        assert result["estimated_remaining_income"] == 54000.0

    def test_zero_bank_credit(self):
        result = calculate_statement_metrics(bank_avg_credit=0.0, detected_emi=18000.0)
        assert result["salary_to_emi_percent"] == 0.0

    def test_no_emi(self):
        result = calculate_statement_metrics(bank_avg_credit=72000.0, detected_emi=0.0)
        assert result["salary_to_emi_percent"] == 0.0
        assert result["estimated_remaining_income"] == 72000.0


# ==========================================================================
# 6. Discrepancy Detection Tests
# ==========================================================================

class TestDetectDiscrepancies:
    """Tests for detect_discrepancies: anomaly generation from comparisons."""

    def _make_comparison(self, field, status, **kwargs):
        return FieldComparison(field=field, status=status, **kwargs)

    def test_no_anomalies_clean(self):
        comparisons = [self._make_comparison("declared_vs_kyc_name", "MATCH")]
        income_calc = {"income_difference_percent": 3.0, "income_difference": 2000}
        obligation_calc = {
            "undisclosed_liability_gap": 0.0, "detected_emi": 0.0,
            "declared_emi": 0.0, "has_undisclosed_liabilities": False,
            "dti_percent": 15.0,
        }
        anomalies = detect_discrepancies(comparisons, income_calc, obligation_calc)
        assert len(anomalies) == 0

    def test_identity_mismatch_anomaly(self):
        comparisons = [
            self._make_comparison("declared_vs_kyc_name", "MISMATCH", reason="Name mismatch")
        ]
        income_calc = {"income_difference_percent": 0.0, "income_difference": 0}
        obligation_calc = {
            "undisclosed_liability_gap": 0.0, "detected_emi": 0.0,
            "declared_emi": 0.0, "has_undisclosed_liabilities": False,
            "dti_percent": 0.0,
        }
        anomalies = detect_discrepancies(comparisons, income_calc, obligation_calc)
        assert len(anomalies) >= 1
        assert any(a.severity == "HIGH" for a in anomalies)

    def test_severe_income_discrepancy(self):
        comparisons = []
        income_calc = {"income_difference_percent": 25.0, "income_difference": 25000}
        obligation_calc = {
            "undisclosed_liability_gap": 0.0, "detected_emi": 0.0,
            "declared_emi": 0.0, "has_undisclosed_liabilities": False,
            "dti_percent": 0.0,
        }
        anomalies = detect_discrepancies(comparisons, income_calc, obligation_calc)
        severe = [a for a in anomalies if a.code == "SEVERE_INCOME_DISCREPANCY"]
        assert len(severe) == 1
        assert severe[0].severity == "HIGH"

    def test_moderate_income_discrepancy(self):
        comparisons = []
        income_calc = {"income_difference_percent": 15.0, "income_difference": 12000}
        obligation_calc = {
            "undisclosed_liability_gap": 0.0, "detected_emi": 0.0,
            "declared_emi": 0.0, "has_undisclosed_liabilities": False,
            "dti_percent": 0.0,
        }
        anomalies = detect_discrepancies(comparisons, income_calc, obligation_calc)
        inc_anom = [a for a in anomalies if "INCOME" in a.code]
        assert len(inc_anom) == 1
        assert inc_anom[0].severity == "MEDIUM"

    def test_critical_high_dti(self):
        comparisons = []
        income_calc = {"income_difference_percent": 0.0, "income_difference": 0}
        obligation_calc = {
            "undisclosed_liability_gap": 0.0, "detected_emi": 0.0,
            "declared_emi": 0.0, "has_undisclosed_liabilities": False,
            "dti_percent": 70.0,
        }
        anomalies = detect_discrepancies(comparisons, income_calc, obligation_calc)
        dti_anom = [a for a in anomalies if "DTI" in a.code]
        assert len(dti_anom) == 1
        assert dti_anom[0].severity == "HIGH"

    def test_statement_mismatch_anomaly(self):
        comparisons = []
        income_calc = {"income_difference_percent": 0.0, "income_difference": 0}
        obligation_calc = {
            "undisclosed_liability_gap": 0.0, "detected_emi": 0.0,
            "declared_emi": 0.0, "has_undisclosed_liabilities": False,
            "dti_percent": 0.0,
        }
        statement_calc = {"status": "MISMATCH", "difference_amount": 25000.0, "message": "Balance mismatch"}
        anomalies = detect_discrepancies(
            comparisons, income_calc, obligation_calc, statement_calc=statement_calc
        )
        stmt_anom = [a for a in anomalies if a.code == "STATEMENT_ARITHMETIC_MISMATCH"]
        assert len(stmt_anom) == 1
        assert stmt_anom[0].severity == "HIGH"

    def test_eligibility_failure_anomaly(self):
        comparisons = []
        income_calc = {"income_difference_percent": 0.0, "income_difference": 0}
        obligation_calc = {
            "undisclosed_liability_gap": 0.0, "detected_emi": 0.0,
            "declared_emi": 0.0, "has_undisclosed_liabilities": False,
            "dti_percent": 0.0,
        }
        eligibility_calc = {"passed": False, "reasons": ["Income below minimum"]}
        anomalies = detect_discrepancies(
            comparisons, income_calc, obligation_calc, eligibility_calc=eligibility_calc
        )
        elig_anom = [a for a in anomalies if a.code == "POLICY_ELIGIBILITY_FAILURE"]
        assert len(elig_anom) >= 1

    def test_major_undisclosed_liability(self):
        comparisons = []
        income_calc = {"income_difference_percent": 0.0, "income_difference": 0}
        obligation_calc = {
            "undisclosed_liability_gap": 15000.0, "detected_emi": 20000.0,
            "declared_emi": 5000.0, "has_undisclosed_liabilities": True,
            "dti_percent": 30.0,
        }
        anomalies = detect_discrepancies(comparisons, income_calc, obligation_calc)
        major = [a for a in anomalies if a.code == "MAJOR_UNDISCLOSED_LIABILITY"]
        assert len(major) == 1
        assert major[0].severity == "HIGH"

    def test_all_anomaly_types_are_valid(self):
        comparisons = [
            self._make_comparison("declared_vs_kyc_name", "MISMATCH"),
            self._make_comparison("pan_number", "PARTIAL_MATCH"),
        ]
        income_calc = {"income_difference_percent": 25.0, "income_difference": 25000}
        obligation_calc = {
            "undisclosed_liability_gap": 15000.0, "detected_emi": 20000.0,
            "declared_emi": 5000.0, "has_undisclosed_liabilities": True,
            "dti_percent": 70.0,
        }
        statement_calc = {"status": "MISMATCH", "difference_amount": 25000.0}
        eligibility_calc = {"passed": False, "reasons": ["Income below minimum"]}
        anomalies = detect_discrepancies(
            comparisons, income_calc, obligation_calc,
            statement_calc=statement_calc, eligibility_calc=eligibility_calc
        )
        for a in anomalies:
            assert isinstance(a, Anomaly)
            assert a.severity in ("LOW", "MEDIUM", "HIGH")
            assert a.code
            assert a.source
