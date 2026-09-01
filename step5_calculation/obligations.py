from typing import Dict, Any, List


def calculate_obligations(
    detected_emi: float,
    declared_liabilities: List[dict] | None = None,
    verified_monthly_net: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate existing financial obligations.

    detected_emi:
        EMI amount detected from bank transactions.

    declared_liabilities:
        Liabilities declared in loan application.

    verified_monthly_net:
        Verified monthly income.
    """

    detected_emi = float(
        detected_emi or 0
    )

    verified_monthly_net = float(
        verified_monthly_net or 0
    )

    declared_liabilities = (
        declared_liabilities
        or []
    )

    # --------------------------------------------------
    # Declared liability count
    # --------------------------------------------------

    declared_liability_count = len(
        declared_liabilities
    )

    # --------------------------------------------------
    # DTI calculation
    # --------------------------------------------------

    if verified_monthly_net > 0:

        dti_percent = round(
            (
                detected_emi
                / verified_monthly_net
            ) * 100,
            2
        )

    else:

        dti_percent = 0.0

    # --------------------------------------------------
    # DTI category
    # --------------------------------------------------

    if verified_monthly_net <= 0:

        dti_status = "NOT_AVAILABLE"

    elif dti_percent <= 30:

        dti_status = "LOW"

    elif dti_percent <= 50:

        dti_status = "MODERATE"

    else:

        dti_status = "HIGH"

    return {

        "detected_emi":
            round(
                detected_emi,
                2
            ),

        "declared_liability_count":
            declared_liability_count,

        "declared_liabilities":
            declared_liabilities,

        "dti_percent":
            dti_percent,

        "dti_status":
            dti_status,
    }