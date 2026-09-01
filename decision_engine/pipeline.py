import importlib
from typing import Any

from database.db_config import get_db
from database import crud

from comparison_engine.app.pipeline import (
    build_pipeline_result,
)

from step5_calculation import (
    calculate_income,
    calculate_obligations,
    calculate_statement_metrics,
    calculate_eligibility,
)

from step6_risk_anomaly import (
    detect_discrepancies,
    classify_anomalies,
    calculate_risk_score,
)

from .schemas import FinalDecision


def run_decision_pipeline(
    application_id: str,
    policy_name: str = "personal_loan",
    db: Any = None,
) -> FinalDecision:

    # ---------------------------------------------------------
    # 1. DATABASE
    # ---------------------------------------------------------

    if db is None:
        db = get_db()

    application = crud.get_application(
        db,
        application_id
    )

    if not application:
        raise ValueError(
            f"Application '{application_id}' not found."
        )

    # ---------------------------------------------------------
    # 2. COMPARISON ENGINE
    # ---------------------------------------------------------

    print(
        f"[DECISION] Running comparison for {application_id}"
    )

    comparison_result = build_pipeline_result(
        application
    )

    comparison_dict = comparison_result.model_dump(
        mode="python"
    )

    crud.update_comparison_result(
        db,
        application_id,
        comparison_dict
    )

    # ---------------------------------------------------------
    # 3. EXTRACT DOCUMENTS
    # ---------------------------------------------------------

    documents = application.get(
        "documents",
        []
    ) or []

    payslips = [
        d
        for d in documents
        if d.get("doc_type", "").upper() == "PAYSLIP"
    ]

    bank_statements = [
        d
        for d in documents
        if d.get("doc_type", "").upper()
        == "BANK_STATEMENT"
    ]

    loan_applications = [
        d
        for d in documents
        if d.get("doc_type", "").upper()
        == "LOAN_APPLICATION"
    ]

    form16s = [
        d
        for d in documents
        if d.get("doc_type", "").upper()
        == "FORM16"
    ]

    # ---------------------------------------------------------
    # 4. DECLARED FINANCIAL INFORMATION
    # ---------------------------------------------------------

    loan_ext = (
        loan_applications[0].get("extracted") or {}
        if loan_applications
        else {}
    )

    financials = (
        application.get("financials")
        or {}
    )

    loan_request = (
        financials.get("loan_request")
        or {}
    )

    declared_income = float(
        loan_ext.get("net_monthly")
        or loan_ext.get("gross_monthly")
        or loan_request.get(
            "declared_net_monthly"
        )
        or 0.0
    )

    declared_liabilities = (
        loan_ext.get("liabilities")
        or loan_request.get(
            "declared_liabilities"
        )
        or []
    )

    proposed_emi = float(
        financials.get(
            "proposed_emi"
        )
        or 0.0
    )

    # ---------------------------------------------------------
    # 5. BANK STATEMENT
    # ---------------------------------------------------------

    bank_ext = (
        bank_statements[0].get("extracted") or {}
        if bank_statements
        else {}
    )

    bank_transactions = []

    # If transactions are stored directly in the
    # application document:
    if application.get("bank_transactions"):
        bank_transactions = application.get(
            "bank_transactions"
        ) or []

    # Otherwise read them from extracted bank statement.
    elif bank_ext.get("transactions"):
        bank_transactions = (
            bank_ext.get("transactions")
            or []
        )

    # ---------------------------------------------------------
    # 6. FINANCIAL CALCULATIONS
    # ---------------------------------------------------------

    print(
        f"[DECISION] Running financial calculations..."
    )

    income_metrics = calculate_income(

        declared_income=declared_income,

        payslips=payslips,

        bank_transactions=bank_transactions,

        form16=(
            form16s[0].get("extracted")
            if form16s
            else None
        ),
    )

    obligation_metrics = calculate_obligations(

        declared_liabilities=declared_liabilities,

        bank_transactions=bank_transactions,

        verified_monthly_income=(
            income_metrics.verified_monthly_income
        ),

        proposed_emi=proposed_emi,

        loan_request=(
            loan_request
            or loan_ext
        ),
    )

    statement_result = calculate_statement_metrics(

        opening_balance=float(
            bank_ext.get(
                "opening_balance"
            )
            or 0.0
        ),

        total_credits=float(
            bank_ext.get(
                "total_credits"
            )
            or 0.0
        ),

        total_debits=float(
            bank_ext.get(
                "total_debits"
            )
            or 0.0
        ),

        closing_balance=float(
            bank_ext.get(
                "closing_balance"
            )
            or 0.0
        ),
    )

    eligibility_result = calculate_eligibility(

        verified_income=(
            income_metrics.verified_monthly_income
        ),

        foir_percentage=(
            obligation_metrics.foir_percentage
        ),

        income_variance_percent=(
            income_metrics.income_variance_percent
        ),

        undisclosed_liability_gap=(
            obligation_metrics.undisclosed_liability_gap
        ),

        policy_name=policy_name,
    )

    # ---------------------------------------------------------
    # 7. DISCREPANCY DETECTION
    # ---------------------------------------------------------

    print(
        f"[DECISION] Detecting discrepancies..."
    )

    discrepancies = detect_discrepancies(

        application_data=application,

        income_metrics=income_metrics,

        obligation_metrics=obligation_metrics,

        statement_result=statement_result,

        eligibility_result=eligibility_result,

        extracted_fields=None,

        # IMPORTANT:
        # comparison_result contains identity comparison
        # information generated by your comparison engine.
        step4_result=comparison_result,
    )

    # ---------------------------------------------------------
    # 8. LLM ANOMALY ASSESSMENT
    # ---------------------------------------------------------

    print(
        f"[DECISION] Classifying anomaly severity..."
    )

    anomaly_assessment, is_llm_fallback = (
        classify_anomalies(

            applicant_data=application,

            income_metrics=income_metrics,

            obligation_metrics=obligation_metrics,

            statement_result=statement_result,

            eligibility_result=eligibility_result,

            discrepancies=discrepancies,
        )
    )

    # ---------------------------------------------------------
    # 9. RISK SCORING
    # ---------------------------------------------------------

    print(
        f"[DECISION] Calculating risk score..."
    )

    classified_anomalies = [
        anomaly.model_dump()
        for anomaly
        in anomaly_assessment.anomalies
    ]

    risk_result = calculate_risk_score(

        income_metrics=income_metrics,

        obligation_metrics=obligation_metrics,

        statement_result=statement_result,

        eligibility_result=eligibility_result,

        classified_anomalies=classified_anomalies,

        is_llm_fallback=is_llm_fallback,

        policy_name=policy_name,
    )

    # ---------------------------------------------------------
    # 10. SAVE RISK ASSESSMENT
    # ---------------------------------------------------------

    crud.update_risk_assessment(
        db,
        application_id,
        anomaly_assessment.model_dump(
            mode="python"
        )
    )

    # ---------------------------------------------------------
    # 11. SAVE RISK RESULT
    # ---------------------------------------------------------

    crud.update_risk_result(
        db,
        application_id,
        risk_result.model_dump(
            mode="python"
        )
    )

    # ---------------------------------------------------------
    # 12. FINAL DECISION
    # ---------------------------------------------------------

    if risk_result.routing_color == "green":

        status = "approved"

    elif risk_result.routing_color == "amber":

        status = "review"

    else:

        status = "rejected"

    final_decision = FinalDecision(

        application_id=application_id,

        status=status,

        routing_color=(
            risk_result.routing_color
        ),

        recommendation=(
            risk_result.recommendation
        ),

        risk_score=(
            risk_result.score
        ),

        risk_grade=(
            risk_result.grade
        ),

        comparison_result=(
            comparison_result
        ),

        income_metrics=(
            income_metrics
        ),

        obligation_metrics=(
            obligation_metrics
        ),

        statement_validation=(
            statement_result
        ),

        eligibility_result=(
            eligibility_result
        ),

        anomaly_assessment=(
            anomaly_assessment
        ),

        risk_result=(
            risk_result
        ),

        is_llm_fallback=(
            is_llm_fallback
        ),

        underwriting_summary=(
            anomaly_assessment.underwriting_summary
        ),
    )

    # ---------------------------------------------------------
    # 13. SAVE FINAL DECISION
    # ---------------------------------------------------------

    crud.update_final_decision(

        db,

        application_id,

        {
            "status": final_decision.status,

            "routing_color": (
                final_decision.routing_color
            ),

            "recommendation": (
                final_decision.recommendation
            ),

            "risk_score": (
                final_decision.risk_score
            ),

            "risk_grade": (
                final_decision.risk_grade
            ),

            "underwriting_summary": (
                final_decision.underwriting_summary
            ),

            "is_llm_fallback": (
                final_decision.is_llm_fallback
            ),
        }
    )

    # ---------------------------------------------------------
    # 14. AUDIT LOG
    # ---------------------------------------------------------

    crud.log_audit_event(

        db,

        application_id,

        action="decision_pipeline_completed",

        detail={

            "risk_score": (
                risk_result.score
            ),

            "risk_grade": (
                risk_result.grade
            ),

            "routing": (
                risk_result.routing_color
            ),

            "recommendation": (
                risk_result.recommendation
            ),

            "discrepancy_count": (
                len(discrepancies)
            ),

            "anomaly_count": (
                len(
                    anomaly_assessment.anomalies
                )
            ),

            "llm_fallback": (
                is_llm_fallback
            ),
        }
    )

    print(
        f"[DECISION] Completed: "
        f"{risk_result.routing_color.upper()}"
    )

    return final_decision