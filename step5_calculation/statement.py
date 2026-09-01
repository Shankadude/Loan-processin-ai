from typing import Dict, Any


def calculate_statement_metrics(
    bank_avg_salary_credit: float = 0.0,
    detected_emi: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate financial metrics derived from
    the bank statement.
    """

    bank_avg_salary_credit = float(
        bank_avg_salary_credit or 0
    )

    detected_emi = float(
        detected_emi or 0
    )

    # --------------------------------------------------
    # Salary-to-EMI ratio
    # --------------------------------------------------

    if bank_avg_salary_credit > 0:

        salary_to_emi_percent = round(
            (
                detected_emi
                / bank_avg_salary_credit
            ) * 100,
            2
        )

    else:

        salary_to_emi_percent = 0.0

    # --------------------------------------------------
    # Remaining income after EMI
    # --------------------------------------------------

    remaining_income = max(
        bank_avg_salary_credit
        - detected_emi,
        0
    )

    return {

        "bank_avg_salary_credit":
            round(
                bank_avg_salary_credit,
                2
            ),

        "detected_emi":
            round(
                detected_emi,
                2
            ),

        "salary_to_emi_percent":
            salary_to_emi_percent,

        "estimated_remaining_income":
            round(
                remaining_income,
                2
            ),
    }