from .extractors import (
    extract_declared,
    extract_verified,
    extract_liabilities
)

from .comparison import (
    compare_identity,
    compare_income,
    compare_employer,
    compare_pan
)

from .llm_semantic import (
    semantic_compare
)

from .discrepancy import (
    classify_discrepancies
)

from .models import (
    ComparisonResult,
    Evidence
)

from .policy_engine import (
    calculate_risk
)


def build_pipeline_result(
    payload
):
    # STEP 1
    # NORMALIZATION / EXTRACTION


    declared = extract_declared(
        payload
    )

    verified = extract_verified(
        payload
    )

    liabilities = extract_liabilities(
        payload
    )
    # STEP 2
    # DETERMINISTIC COMPARISON
    identity_results = compare_identity(
        declared,
        verified
    )

    identity_results.append(
        compare_pan(
            payload,
            verified
        )
    )

    income_result = compare_income(
        declared,
        verified
    )

    employer_result = compare_employer(
        declared,
        verified
    )

    deterministic_results = (

        identity_results

        +
        [
            income_result,
            employer_result
        ]
    )

    # STEP 3
    # LLM SEMANTIC COMPARISON


    semantic_results = semantic_compare(
        declared,
        verified
    )

    identity_statuses = [

        result.status

        for result in identity_results
    ]

    if "MISMATCH" in identity_statuses:

        identity_status = "MISMATCH"

    elif "PARTIAL_MATCH" in identity_statuses:

        identity_status = "PARTIAL_MATCH"

    elif all(
        status == "MATCH"
        for status in identity_statuses
    ):

        identity_status = "MATCH"

    else:

        identity_status = "NOT_AVAILABLE"

    # STEP 5
    # INCOME

    declared_net = float(
        declared.get(
            "net_monthly"
        )
        or 0
    )

    verified_net = float(
        verified.get(
            "payslip_net_monthly"
        )
        or 0
    )

    income_difference = abs(
        declared_net
        -
        verified_net
    )

    income_difference_percent = (

        round(

            income_difference
            /
            declared_net
            *
            100,

            2
        )

        if declared_net > 0

        else 0
    )

    if income_result.status == "MISMATCH":

        income_status = "MISMATCH"

    elif income_result.status == "PARTIAL_MATCH":

        income_status = "PARTIAL_MATCH"

    else:

        income_status = income_result.status

    # STEP 6
    # LIABILITY
    declared_liabilities = (

        liabilities[
            "declared_liabilities"
        ]
    )

    detected_emi = (

        liabilities[
            "detected_emi"
        ]
    )

    if (
        not declared_liabilities
        and
        detected_emi == 0
    ):

        liability_status = "MATCH"

    elif (
        not declared_liabilities
        and
        detected_emi > 0
    ):

        liability_status = "MISMATCH"

    else:

        liability_status = "PARTIAL_MATCH"

   
    # STEP 7
    # OVERALL STATUS

    statuses = [

        identity_status,
        income_status,
        liability_status
    ]

    if "MISMATCH" in statuses:

        overall_status = "MISMATCH"

    elif "PARTIAL_MATCH" in statuses:

        overall_status = "PARTIAL_MATCH"

    else:

        overall_status = "MATCH"
    dti = (

        round(
            detected_emi
            /
            verified_net
            *
            100,
            2
        )

        if verified_net > 0

        else 0
    )
    # STEP 9
    # ANOMALIES
    anomalies = classify_discrepancies(

        income_result,

        identity_status,

        liability_status,

        detected_emi,

        declared_net,

        verified_net
    )
    # STEP 10
    # BUILD RESULT

    result = ComparisonResult(

        applicant_id=str(
            payload.get(
                "_id",
                ""
            )
        ),

        identity_status=
            identity_status,

        income_status=
            income_status,

        liability_status=
            liability_status,

        overall_status=
            overall_status,

        declared_monthly_net=
            declared_net,

        verified_monthly_net=
            verified_net,

        income_difference=
            round(
                income_difference,
                2
            ),

        income_difference_percent=
            income_difference_percent,

        declared_emi=
            0.0,

        detected_emi=
            detected_emi,

        dti_percent=
            dti,

        discrepancies=
            deterministic_results,

        semantic_findings=
            semantic_results,

        anomalies=
            anomalies,

        evidence=[

            Evidence(

                source_document=
                    "BANK_STATEMENT",

                source_path=
                    "transactions[]",

                field=
                    "detected_emi",

                value=
                    detected_emi,

                evidence_type=
                    "DERIVED",

                note=
                    "Only transactions classified "
                    "as emi_debit are counted."
            )
        ],

        risk_level="LOW",

        recommendation=
            "REVIEW",

        audit_notes=""
    )
    # SEND TO RISK ENGINE
   
    result = calculate_risk(
        result
    )

    return result