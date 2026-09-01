from typing import Dict, Any

from pydantic import BaseModel


class IncomeMetrics(BaseModel):
    declared_monthly_net: float
    verified_monthly_net: float
    bank_avg_salary_credit: float

    effective_verified_income: float

    income_difference: float
    income_difference_percent: float



def calculate_income(
    declared_monthly_net: float,
    verified_monthly_net: float,
    bank_avg_salary_credit: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate verified income metrics.

    Inputs:
        declared_monthly_net:
            Net monthly income declared by applicant.

        verified_monthly_net:
            Average net income obtained from payslips.

        bank_avg_salary_credit:
            Average salary credit detected from bank statement.

    Returns:
        Dictionary containing income calculations.
    """

    declared_monthly_net = float(
        declared_monthly_net or 0
    )

    verified_monthly_net = float(
        verified_monthly_net or 0
    )

    bank_avg_salary_credit = float(
        bank_avg_salary_credit or 0
    )

    # --------------------------------------------------
    # Income difference
    # --------------------------------------------------

    income_difference = abs(
        declared_monthly_net
        - verified_monthly_net
    )

    # --------------------------------------------------
    # Income difference percentage
    # --------------------------------------------------

    if declared_monthly_net > 0:

        income_difference_percent = round(
            (
                income_difference
                / declared_monthly_net
            ) * 100,
            2
        )

    else:

        income_difference_percent = 0.0

    # --------------------------------------------------
    # Conservative verified income
    # --------------------------------------------------
    # We prefer payslip income when available.
    # Bank salary credit is used as supporting evidence.

    if verified_monthly_net > 0:

        effective_verified_income = verified_monthly_net

    elif bank_avg_salary_credit > 0:

        effective_verified_income = bank_avg_salary_credit

    else:

        effective_verified_income = 0.0

    return {

        "declared_monthly_net":
            declared_monthly_net,

        "verified_monthly_net":
            verified_monthly_net,

        "bank_avg_salary_credit":
            bank_avg_salary_credit,

        "effective_verified_income":
            round(
                effective_verified_income,
                2
            ),

        "income_difference":
            round(
                income_difference,
                2
            ),

        "income_difference_percent":
            income_difference_percent,
    }