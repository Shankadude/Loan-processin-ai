from .income import calculate_verified_income
from .obligation import calculate_obligations
from .statement import validate_statement_arithmetic
from .eligibility import check_eligibility
from .models import RiskAssessmentResult


def run_risk_assessment(
    applicant_id: str,
    declared_income: float,
    payslips: list[dict],
    bank_transactions: list[dict],
    declared_liabilities: list[dict],
    statement_data: dict,
    loan_request: dict | None = None,
) -> RiskAssessmentResult:

    # =====================================================
    # STEP 1: VERIFY INCOME
    # =====================================================

    income_result = calculate_verified_income(
        declared_income=declared_income,
        payslips=payslips,
        bank_transactions=bank_transactions,
    )

    # =====================================================
    # STEP 2: CALCULATE OBLIGATIONS + FOIR
    # =====================================================

    obligation_result = calculate_obligations(
        declared_liabilities=declared_liabilities,
        bank_transactions=bank_transactions,
        verified_monthly_income=income_result.verified_monthly_income,
        loan_request=loan_request,
    )

    # =====================================================
    # STEP 3: VALIDATE BANK STATEMENT
    # =====================================================

    statement_result = validate_statement_arithmetic(
        opening_balance=statement_data.get("opening_balance", 0),
        total_credits=statement_data.get("total_credits", 0),
        total_debits=statement_data.get("total_debits", 0),
        closing_balance=statement_data.get("closing_balance", 0),
    )

    # =====================================================
    # STEP 4: POLICY ELIGIBILITY
    # =====================================================

    eligibility_result = check_eligibility(
        verified_income=income_result.verified_monthly_income,
        foir_percentage=obligation_result.foir_percentage,
        income_variance_percent=income_result.income_variance_percent,
        undisclosed_liability_gap=obligation_result.undisclosed_liability_gap,
    )

    # =====================================================
    # STEP 5: RISK SCORING
    # =====================================================

    risk_score = calculate_risk_score(
        income=income_result,
        obligations=obligation_result,
        statement=statement_result,
        eligibility=eligibility_result,
    )

    # =====================================================
    # STEP 6: RISK LEVEL
    # =====================================================

    if risk_score >= 70:
        risk_level = "LOW"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    # =====================================================
    # STEP 7: RECOMMENDATION
    # =====================================================

    if eligibility_result.passed and risk_level == "LOW":
        recommendation = "APPROVE"

    elif risk_level == "MEDIUM":
        recommendation = "MANUAL_REVIEW"

    else:
        recommendation = "REJECT"

    # =====================================================
    # FINAL RESULT
    # =====================================================

    return RiskAssessmentResult(
        applicant_id=applicant_id,
        income=income_result,
        obligations=obligation_result,
        statement=statement_result,
        eligibility=eligibility_result,
        risk_score=risk_score,
        risk_level=risk_level,
        recommendation=recommendation,
    )