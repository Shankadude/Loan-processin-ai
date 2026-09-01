from typing import Any, Dict, List


def detect_discrepancies(
    comparison_result: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Detect discrepancies from the Comparison Engine result.

    This function does NOT calculate the final risk score.
    It only identifies potential anomalies.
    """

    anomalies = []

    # --------------------------------------------------
    # Identity mismatch
    # --------------------------------------------------

    identity_status = comparison_result.get(
        "identity_status"
    )

    if identity_status == "MISMATCH":

        anomalies.append({
            "code": "IDENTITY_MISMATCH",

            "severity": "HIGH",

            "description":
                "Declared identity information does not "
                "match verified identity information.",

            "source":
                "comparison_engine",

            "evidence": {
                "identity_status":
                    identity_status
            }
        })

    elif identity_status == "PARTIAL_MATCH":

        anomalies.append({
            "code": "IDENTITY_PARTIAL_MATCH",

            "severity": "MEDIUM",

            "description":
                "Some identity fields partially match "
                "while others require review.",

            "source":
                "comparison_engine",

            "evidence": {
                "identity_status":
                    identity_status
            }
        })

    # --------------------------------------------------
    # Income mismatch
    # --------------------------------------------------

    income_status = comparison_result.get(
        "income_status"
    )

    income_difference_percent = float(
        comparison_result.get(
            "income_difference_percent",
            0
        ) or 0
    )

    if income_difference_percent > 10:

        anomalies.append({
            "code": "INCOME_DISCREPANCY",

            "severity": "HIGH",

            "description":
                "Declared income differs from verified "
                "income by more than 10%.",

            "source":
                "comparison_engine",

            "evidence": {
                "income_status":
                    income_status,

                "difference_percent":
                    income_difference_percent
            }
        })

    elif income_difference_percent > 5:

        anomalies.append({
            "code": "INCOME_PARTIAL_DISCREPANCY",

            "severity": "MEDIUM",

            "description":
                "Declared income differs from verified "
                "income by more than 5%.",

            "source":
                "comparison_engine",

            "evidence": {
                "income_status":
                    income_status,

                "difference_percent":
                    income_difference_percent
            }
        })

    # --------------------------------------------------
    # Liability mismatch
    # --------------------------------------------------

    liability_status = comparison_result.get(
        "liability_status"
    )

    detected_emi = float(
        comparison_result.get(
            "detected_emi",
            0
        ) or 0
    )

    if (
        liability_status == "MISMATCH"
        and detected_emi > 0
    ):

        anomalies.append({
            "code": "UNDISCLOSED_LIABILITY",

            "severity": "HIGH",

            "description":
                "EMI transactions were detected in the "
                "bank statement but corresponding "
                "liabilities were not declared.",

            "source":
                "comparison_engine",

            "evidence": {
                "liability_status":
                    liability_status,

                "detected_emi":
                    detected_emi
            }
        })

    # --------------------------------------------------
    # High DTI
    # --------------------------------------------------

    dti_percent = float(
        comparison_result.get(
            "dti_percent",
            0
        ) or 0
    )

    if dti_percent > 50:

        anomalies.append({
            "code": "HIGH_DTI",

            "severity": "HIGH",

            "description":
                "Detected EMI obligations exceed "
                "50% of verified monthly income.",

            "source":
                "step5_calculation",

            "evidence": {
                "dti_percent":
                    dti_percent
            }
        })

    elif dti_percent > 30:

        anomalies.append({
            "code": "ELEVATED_DTI",

            "severity": "MEDIUM",

            "description":
                "Debt-to-income ratio is above 30%.",

            "source":
                "step5_calculation",

            "evidence": {
                "dti_percent":
                    dti_percent
            }
        })

    return anomalies