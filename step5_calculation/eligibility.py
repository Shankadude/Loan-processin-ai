from typing import Dict, Any


def calculate_eligibility(
    verified_monthly_net: float,
    dti_percent: float,
    loan_amount_requested: float = 0.0,
    tenure_months: int = 0,
) -> Dict[str, Any]:
    """
    Calculate basic financial eligibility indicators.

    This module does NOT make the final loan decision.
    Final risk and decision logic belongs to the
    risk/decision engine.
    """

    verified_monthly_net = float(
        verified_monthly_net or 0
    )

    dti_percent = float(
        dti_percent or 0
    )

    loan_amount_requested = float(
        loan_amount_requested or 0
    )

    tenure_months = int(
        tenure_months or 0
    )

    # --------------------------------------------------
    # Basic income availability
    # --------------------------------------------------

    income_available = (
        verified_monthly_net > 0
    )

    # --------------------------------------------------
    # DTI eligibility indicator
    # --------------------------------------------------

    if dti_percent <= 30:

        dti_eligibility = "GOOD"

    elif dti_percent <= 50:

        dti_eligibility = "MODERATE"

    else:

        dti_eligibility = "HIGH"

    # --------------------------------------------------
    # Requested loan / income ratio
    # --------------------------------------------------

    if verified_monthly_net > 0:

        loan_to_monthly_income = round(
            loan_amount_requested
            / verified_monthly_net,
            2
        )

    else:

        loan_to_monthly_income = 0.0

    return {

        "income_available":
            income_available,

        "dti_eligibility":
            dti_eligibility,

        "loan_amount_requested":
            loan_amount_requested,

        "tenure_months":
            tenure_months,

        "loan_to_monthly_income":
            loan_to_monthly_income,
    }