def classify_discrepancies(
    income_result,
    identity_status,
    liability_status,
    detected_emi,
    declared_net,
    verified_net,
):
    anomalies = []

    # =====================================================
    # INCOME
    # =====================================================

    if (
        declared_net > 0
        and verified_net > 0
    ):

        difference_percent = (
            abs(
                declared_net
                - verified_net
            )
            / declared_net
            * 100
        )

        if difference_percent > 10:

            anomalies.append(
                "INCOME_OVERSTATED"
            )


    # =====================================================
    # IDENTITY
    # =====================================================

    if identity_status == "MISMATCH":

        anomalies.append(
            "IDENTITY_MISMATCH"
        )


    # =====================================================
    # LIABILITY
    # =====================================================

    if (
        liability_status == "MISMATCH"
        and detected_emi > 0
    ):

        anomalies.append(
            "UNDISCLOSED_LIABILITY"
        )


    return anomalies