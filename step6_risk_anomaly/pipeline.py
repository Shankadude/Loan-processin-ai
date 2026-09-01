from typing import Any, Dict

from .schemas import RiskAssessment
from .discrepancy import detect_discrepancies
from .anomaly_classifier import classify_anomalies
from .risk_rules import calculate_risk_score


def assess_risk(
    comparison_result: Dict[str, Any]
) -> RiskAssessment:
    """
    Execute the complete Step 6 risk and anomaly pipeline.

    Input:
        Comparison Engine result + Step 5 metrics.

    Output:
        Structured RiskAssessment.
    """

    applicant_id = str(
        comparison_result.get(
            "applicant_id",
            ""
        )
    )

    # --------------------------------------------------
    # STEP 1
    # Detect anomalies
    # --------------------------------------------------

    detected_anomalies = detect_discrepancies(
        comparison_result
    )

    # --------------------------------------------------
    # STEP 2
    # Classify anomalies
    # --------------------------------------------------

    anomalies = classify_anomalies(
        detected_anomalies
    )

    # --------------------------------------------------
    # STEP 3
    # Calculate risk score
    # --------------------------------------------------

    risk_score, risk_factors = calculate_risk_score(
        anomalies
    )

    # --------------------------------------------------
    # STEP 4
    # Risk level
    # --------------------------------------------------

    if risk_score >= 70:

        risk_level = "HIGH"

        recommendation = "REJECT"

    elif risk_score >= 30:

        risk_level = "MEDIUM"

        recommendation = "REVIEW"

    else:

        risk_level = "LOW"

        recommendation = "AUTO_APPROVE"

    # --------------------------------------------------
    # STEP 5
    # Audit notes
    # --------------------------------------------------

    if risk_factors:

        audit_notes = " ".join(
            factor.reason
            for factor in risk_factors
        )

    else:

        audit_notes = (
            "No significant risk factors detected."
        )

    # --------------------------------------------------
    # STEP 6
    # Final assessment
    # --------------------------------------------------

    return RiskAssessment(

        applicant_id=applicant_id,

        risk_score=risk_score,

        risk_level=risk_level,

        recommendation=recommendation,

        risk_factors=risk_factors,

        anomalies=anomalies,

        audit_notes=audit_notes,
    )