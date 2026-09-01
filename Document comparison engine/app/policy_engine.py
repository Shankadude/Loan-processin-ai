def calculate_risk(result):

    score = 0

    reasons = []

    # -------------------------
    # INCOME
    # -------------------------

    if result.income_difference_percent > 10:

        score += 35

        reasons.append(
            "Declared income exceeds "
            "verified income by more than 10%."
        )

    # -------------------------
    # IDENTITY
    # -------------------------

    if result.identity_status == "MISMATCH":

        score += 60

        reasons.append(
            "Identity mismatch detected."
        )

    # -------------------------
    # LIABILITY
    # -------------------------

    if (
        result.liability_status
        ==
        "MISMATCH"
    ):

        score += 30

        reasons.append(
            "Potential undisclosed liability."
        )

    # -------------------------
    # DTI
    # -------------------------

    if result.dti_percent > 50:

        score += 35

        reasons.append(
            "DTI exceeds demo threshold."
        )

    # -------------------------
    # FINAL
    # -------------------------

    if score >= 70:

        result.risk_level = "HIGH"

        result.recommendation = (
            "REJECT"
        )

    elif score >= 30:

        result.risk_level = "MEDIUM"

        result.recommendation = (
            "REVIEW"
        )

    else:

        result.risk_level = "LOW"

        result.recommendation = (
            "AUTO_APPROVE"
        )

    if reasons:

        result.audit_notes = (
            " ".join(reasons)
        )

    else:

        result.audit_notes = (
            "No major demo rule triggered."
        )

    return result