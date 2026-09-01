from typing import List

from .schemas import (
    Anomaly,
    RiskFactor
)


def calculate_risk_score(
    anomalies: List[Anomaly]
) -> tuple[int, List[RiskFactor]]:
    """
    Calculate risk score from detected anomalies.

    Maximum score is capped at 100.
    """

    score = 0

    risk_factors = []

    # --------------------------------------------------
    # IDENTITY MISMATCH
    # --------------------------------------------------

    for anomaly in anomalies:

        if anomaly.code == "IDENTITY_MISMATCH":

            score += 60

            risk_factors.append(
                RiskFactor(
                    factor="IDENTITY_MISMATCH",

                    score=60,

                    severity="HIGH",

                    reason=
                        "Verified identity information "
                        "does not match declared information.",

                    source=
                        anomaly.source
                )
            )

        # --------------------------------------------------
        # INCOME DISCREPANCY
        # --------------------------------------------------

        elif anomaly.code == "INCOME_DISCREPANCY":

            score += 35

            risk_factors.append(
                RiskFactor(
                    factor="INCOME_DISCREPANCY",

                    score=35,

                    severity="HIGH",

                    reason=
                        "Declared income differs significantly "
                        "from verified income.",

                    source=
                        anomaly.source
                )
            )

        # --------------------------------------------------
        # PARTIAL INCOME DISCREPANCY
        # --------------------------------------------------

        elif anomaly.code == "INCOME_PARTIAL_DISCREPANCY":

            score += 15

            risk_factors.append(
                RiskFactor(
                    factor="INCOME_PARTIAL_DISCREPANCY",

                    score=15,

                    severity="MEDIUM",

                    reason=
                        "Declared income has a moderate "
                        "difference from verified income.",

                    source=
                        anomaly.source
                )
            )

        # --------------------------------------------------
        # UNDISCLOSED LIABILITY
        # --------------------------------------------------

        elif anomaly.code == "UNDISCLOSED_LIABILITY":

            score += 30

            risk_factors.append(
                RiskFactor(
                    factor="UNDISCLOSED_LIABILITY",

                    score=30,

                    severity="HIGH",

                    reason=
                        "Existing EMI obligations were detected "
                        "but were not declared.",

                    source=
                        anomaly.source
                )
            )

        # --------------------------------------------------
        # HIGH DTI
        # --------------------------------------------------

        elif anomaly.code == "HIGH_DTI":

            score += 35

            risk_factors.append(
                RiskFactor(
                    factor="HIGH_DTI",

                    score=35,

                    severity="HIGH",

                    reason=
                        "Debt-to-income ratio exceeds "
                        "the defined threshold.",

                    source=
                        anomaly.source
                )
            )

        # --------------------------------------------------
        # ELEVATED DTI
        # --------------------------------------------------

        elif anomaly.code == "ELEVATED_DTI":

            score += 15

            risk_factors.append(
                RiskFactor(
                    factor="ELEVATED_DTI",

                    score=15,

                    severity="MEDIUM",

                    reason=
                        "Debt-to-income ratio is elevated.",

                    source=
                        anomaly.source
                )
            )

        # --------------------------------------------------
        # PARTIAL IDENTITY
        # --------------------------------------------------

        elif anomaly.code == "IDENTITY_PARTIAL_MATCH":

            score += 10

            risk_factors.append(
                RiskFactor(
                    factor="IDENTITY_PARTIAL_MATCH",

                    score=10,

                    severity="MEDIUM",

                    reason=
                        "Some identity fields require "
                        "additional verification.",

                    source=
                        anomaly.source
                )
            )

    # --------------------------------------------------
    # Cap score
    # --------------------------------------------------

    score = min(
        score,
        100
    )

    return score, risk_factors