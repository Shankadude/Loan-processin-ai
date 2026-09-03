from typing import Dict, Any, List, Optional
from src.schemas.decision_models import Anomaly, RiskFactor, DecisionResult, FieldComparison
from src.decision_engine.calculations import (
    calculate_income_metrics,
    calculate_obligation_metrics,
    validate_statement_arithmetic,
    check_eligibility,
)
from src.decision_engine.discrepancy import detect_discrepancies
from src.decision_engine.policy_loader import load_policy


def score_application(
    application_id: str,
    declared_payload: Dict[str, Any],
    verified_payload: Dict[str, Any],
    liabilities_payload: Dict[str, Any],
    comparisons: List[FieldComparison],
    policy_name: str = "personal_loan",
    bank_statement_data: Optional[Dict[str, Any]] = None,
    requested_amount: float = 0.0,
) -> DecisionResult:
    """
    TRACE Deterministic Scoring & Underwriting Engine:
    Zero-hallucination arithmetic risk deductions, 3-tier traffic-light routing,
    dynamic reviewer checklist, and explainable counterfactual synthesis.

    Enhanced with income-slab-based FOIR assessment, EMI affordability checks,
    and FOIR zone-aware risk deductions.
    """
    policy = load_policy(policy_name)
    weights = policy.get("scoring_weights", {})
    thresholds = policy.get("routing_thresholds", {})

    base_score = float(weights.get("base_score", 100.0))
    deduct_major = float(weights.get("major_anomaly_deduction", 45.0))
    deduct_mod = float(weights.get("moderate_anomaly_deduction", 25.0))
    deduct_minor = float(weights.get("minor_anomaly_deduction", 10.0))
    deduct_statement = float(weights.get("arithmetic_mismatch_deduction", 30.0))
    deduct_elig = float(weights.get("eligibility_failure_deduction", 50.0))

    # FOIR-specific deductions from policy
    deduct_foir_marginal = float(weights.get("foir_marginal_breach_deduction", 10.0))
    deduct_foir_moderate = float(weights.get("foir_moderate_breach_deduction", 20.0))
    deduct_foir_severe = float(weights.get("foir_severe_breach_deduction", 35.0))

    green_threshold = float(thresholds.get("green_min_score", 80.0))
    amber_threshold = float(thresholds.get("amber_min_score", 50.0))

    # 1. Income Metrics (Conservative min)
    declared_net = float(declared_payload.get("net_monthly") or declared_payload.get("gross_monthly") or 0.0)
    verified_net = float(verified_payload.get("payslip_net_monthly") or 0.0)
    bank_avg_credit = float(verified_payload.get("bank_avg_salary_credit") or 0.0)
    income_calc = calculate_income_metrics(declared_net, verified_net, bank_avg_credit)

    # 2. Obligation & FOIR Metrics (now with income-slab-aware FOIR)
    detected_emi = float(liabilities_payload.get("detected_emi") or 0.0)
    declared_liabilities = liabilities_payload.get("declared_liabilities", [])
    proposed_emi_val = round(requested_amount * 0.025, 2) if requested_amount > 0 else 0.0

    obligation_calc = calculate_obligation_metrics(
        detected_emi=detected_emi,
        declared_liabilities=declared_liabilities,
        verified_monthly_net=income_calc["effective_verified_income"],
        proposed_emi=proposed_emi_val,
        policy_name=policy_name,
    )

    # 3. Statement Balance Reconciliation
    bs = bank_statement_data or {}
    statement_calc = validate_statement_arithmetic(
        opening_balance=bs.get("opening_balance"),
        total_credits=bs.get("total_credits"),
        total_debits=bs.get("total_debits"),
        closing_balance=bs.get("closing_balance"),
    )

    # 4. Lender Policy Eligibility Check (now with FOIR zone & EMI affordability)
    eligibility_calc = check_eligibility(
        verified_income=income_calc["effective_verified_income"],
        foir_percentage=obligation_calc["foir_percentage"],
        income_variance_percent=income_calc["income_difference_percent"],
        undisclosed_liability_gap=obligation_calc["undisclosed_liability_gap"],
        foir_zone=obligation_calc.get("foir_zone", "SAFE"),
        emi_affordability_passed=obligation_calc.get("emi_affordability_passed", True),
        applicable_foir_threshold=obligation_calc.get("applicable_foir_threshold", 50.0),
        max_eligible_emi=obligation_calc.get("max_eligible_emi", 0.0),
        proposed_emi=obligation_calc.get("proposed_emi", 0.0),
        policy_name=policy_name,
    )

    # 5. Detect & Classify All Anomalies
    anomalies: List[Anomaly] = detect_discrepancies(
        comparisons=comparisons,
        income_calc=income_calc,
        obligation_calc=obligation_calc,
        statement_calc=statement_calc,
        eligibility_calc=eligibility_calc,
        policy_name=policy_name,
    )

    # Resolve High-Level Component Match Statuses
    id_comparisons = [c for c in comparisons if "name" in c.field or "identity" in c.field or c.field in ["dob", "pan_number"]]
    id_statuses = [c.status for c in id_comparisons]
    if "MISMATCH" in id_statuses:
        identity_status = "MISMATCH"
    elif "PARTIAL_MATCH" in id_statuses:
        identity_status = "PARTIAL_MATCH"
    else:
        identity_status = "MATCH" if id_statuses else "NOT_AVAILABLE"

    inc_diff_pct = income_calc["income_difference_percent"]
    income_status = "MISMATCH" if inc_diff_pct > 15.0 else ("PARTIAL_MATCH" if inc_diff_pct > 5.0 else "MATCH")
    liability_status = "MISMATCH" if obligation_calc["has_undisclosed_liabilities"] else "MATCH"

    overall_status = "MISMATCH" if "MISMATCH" in [identity_status, income_status, liability_status] else (
        "PARTIAL_MATCH" if "PARTIAL_MATCH" in [identity_status, income_status, liability_status] else "MATCH"
    )

    # 6. Quantified 100-Point Risk Score Deductions
    major_anomalies = [a for a in anomalies if a.severity == "HIGH"]
    moderate_anomalies = [a for a in anomalies if a.severity == "MEDIUM"]
    minor_anomalies = [a for a in anomalies if a.severity == "LOW"]

    major_deduction = len(major_anomalies) * deduct_major
    moderate_deduction = len(moderate_anomalies) * deduct_mod
    minor_deduction = len(minor_anomalies) * deduct_minor
    statement_deduction = deduct_statement if not statement_calc["is_valid"] else 0.0
    elig_deduction = deduct_elig if not eligibility_calc["passed"] else 0.0

    # 6a. FOIR Zone-Based Scoring Deductions
    foir_zone = obligation_calc.get("foir_zone", "SAFE")
    foir_breach_severity = obligation_calc.get("foir_breach_severity", "none")
    foir_deduction = 0.0
    if foir_breach_severity == "marginal":
        foir_deduction = deduct_foir_marginal
    elif foir_breach_severity == "moderate":
        foir_deduction = deduct_foir_moderate
    elif foir_breach_severity == "severe":
        foir_deduction = deduct_foir_severe

    final_score = base_score - (major_deduction + moderate_deduction + minor_deduction + statement_deduction + elig_deduction + foir_deduction)
    final_score = max(0.0, min(100.0, round(final_score, 1)))

    factor_breakdown = {
        "base_score": base_score,
        "major_anomalies_count": len(major_anomalies),
        "major_anomalies_deduction": -major_deduction,
        "moderate_anomalies_count": len(moderate_anomalies),
        "moderate_anomalies_deduction": -moderate_deduction,
        "minor_anomalies_count": len(minor_anomalies),
        "minor_anomalies_deduction": -minor_deduction,
        "statement_arithmetic_deduction": -statement_deduction,
        "eligibility_failure_deduction": -elig_deduction,
        "foir_zone": foir_zone,
        "foir_breach_severity": foir_breach_severity,
        "foir_zone_deduction": -foir_deduction,
        "applicable_foir_threshold": obligation_calc.get("applicable_foir_threshold", 50.0),
        "foir_headroom": obligation_calc.get("foir_headroom", 0.0),
        "max_eligible_emi": obligation_calc.get("max_eligible_emi", 0.0),
        "final_calculated_score": final_score,
    }

    # 7. 3-Tier Traffic-Light Routing Decision (FOIR-Zone-Aware)
    dti_pct = obligation_calc["dti_percent"]
    has_major = len(major_anomalies) > 0
    foir_is_critical = foir_zone == "CRITICAL"

    if (
        final_score >= green_threshold
        and eligibility_calc["passed"]
        and not has_major
        and len(moderate_anomalies) == 0
        and statement_calc["is_valid"]
        and dti_pct <= 50.0
        and foir_zone in ("SAFE", "STRETCH")
    ):
        routing_color = "GREEN"
        recommendation = "AUTO_APPROVE"
        risk_level = "LOW"
        routing_reason = (
            f"Fast-track: Clean profile, FOIR {dti_pct:.1f}% in {foir_zone} zone "
            f"(slab threshold {obligation_calc.get('applicable_foir_threshold', 50.0):.0f}%), "
            f"zero major anomalies, verified statement arithmetic."
        )
    elif (
        final_score < amber_threshold
        or not eligibility_calc["passed"]
        or has_major
        or foir_is_critical
        or not statement_calc["is_valid"]
    ):
        routing_color = "RED"
        recommendation = "REJECT"
        risk_level = "HIGH"
        reasons = []
        if has_major:
            reasons.append(f"{len(major_anomalies)} critical anomaly detected ({major_anomalies[0].description})")
        if not eligibility_calc["passed"]:
            reasons.append(eligibility_calc["reasons"][0])
        if not statement_calc["is_valid"]:
            reasons.append("Bank statement balance mismatch (potential alteration)")
        if foir_is_critical:
            reasons.append(
                f"FOIR {dti_pct:.1f}% in CRITICAL zone — exceeds high-risk ceiling "
                f"(max eligible EMI: Rs. {obligation_calc.get('max_eligible_emi', 0):,.2f})"
            )
        routing_reason = "; ".join(reasons) if reasons else "Application risk exceeds acceptable lending threshold."
    else:
        routing_color = "AMBER"
        recommendation = "REVIEW"
        risk_level = "MEDIUM"
        routing_reason = (
            f"Moderate risk: FOIR {dti_pct:.1f}% in {foir_zone} zone. "
            f"Routed to Underwriter queue for human-in-the-loop sign-off."
        )

    # 8. Dynamic Underwriter Checklist (FOIR-Enhanced)
    checklist: List[str] = []
    if identity_status != "MATCH":
        checklist.append("Perform manual KYC identity verification against government database (PAN/Aadhaar)")
    if inc_diff_pct > 5.0:
        checklist.append(f"Verify salary credits against payslip net (Income variance: {inc_diff_pct:.1f}%)")
    if obligation_calc["has_undisclosed_liabilities"]:
        checklist.append(f"Inspect bank statement debits for undisclosed EMI obligations (Gap: Rs. {obligation_calc['undisclosed_liability_gap']:,.2f})")
    if not statement_calc["is_valid"]:
        checklist.append(f"Request certified bank statement copy: Arithmetic discrepancy of Rs. {statement_calc['difference_amount']:,.2f}")
    if foir_zone in ("BREACH", "CRITICAL"):
        checklist.append(
            f"FOIR breach ({dti_pct:.1f}%) in {foir_zone} zone — verify additional income sources or "
            f"request co-applicant (Max eligible EMI: Rs. {obligation_calc.get('max_eligible_emi', 0):,.2f})"
        )
    elif foir_zone == "STRETCH":
        checklist.append(
            f"FOIR in STRETCH zone ({dti_pct:.1f}%) — confirm stable income trend and minimal "
            f"discretionary spending (Headroom: {obligation_calc.get('foir_headroom', 0):.1f}%)"
        )
    if not obligation_calc.get("emi_affordability_passed", True):
        checklist.append(
            f"Proposed EMI (Rs. {obligation_calc['proposed_emi']:,.2f}) exceeds max eligible EMI "
            f"(Rs. {obligation_calc.get('max_eligible_emi', 0):,.2f}) — assess repayment capacity"
        )
    if not checklist:
        checklist.append("Confirm applicant identity match across KYC proofs")
        checklist.append("Verify one-click fast-track sign-off for loan disbursement")

    # 9. Counterfactual Reasoning Note (FOIR-Enhanced)
    if routing_color == "GREEN":
        counterfactual = "Meets all automated underwriting guidelines for fast-track approval."
    elif routing_color == "AMBER":
        items = []
        if inc_diff_pct > 5.0:
            items.append("providing updated salary slip or bank reconciliation")
        if obligation_calc["has_undisclosed_liabilities"]:
            items.append("furnishing loan closure letters for closed debts")
        if foir_zone in ("STRETCH", "BREACH"):
            items.append(
                f"reducing total obligations to below {obligation_calc.get('applicable_foir_threshold', 50):.0f}% FOIR "
                f"or adding a co-applicant to increase combined income"
            )
        counterfactual = "Application would qualify for GREEN (Auto-Approval) by " + " and ".join(items) if items else "Providing clean document clarification."
    else:
        counterfactual = f"Application rejected due to high-risk factors: {routing_reason}. To re-qualify, applicant must clear active obligations or resolve document inconsistencies."

    # 10. Audit Notes & Risk Factors
    risk_factors: List[RiskFactor] = [
        RiskFactor(
            factor=a.code,
            score=int(deduct_major if a.severity == "HIGH" else (deduct_mod if a.severity == "MEDIUM" else deduct_minor)),
            severity=a.severity,
            reason=a.description,
            source=a.source,
        )
        for a in anomalies
    ]

    # Add FOIR deduction as a risk factor if applicable
    if foir_deduction > 0:
        risk_factors.append(
            RiskFactor(
                factor="FOIR_ZONE_DEDUCTION",
                score=int(foir_deduction),
                severity="HIGH" if foir_breach_severity == "severe" else ("MEDIUM" if foir_breach_severity == "moderate" else "LOW"),
                reason=f"FOIR {dti_pct:.1f}% in {foir_zone} zone (threshold: {obligation_calc.get('applicable_foir_threshold', 50):.0f}%, headroom: {obligation_calc.get('foir_headroom', 0):.1f}%)",
                source="foir_assessment",
            )
        )

    audit_notes = routing_reason

    # Package Step Payloads
    step4_payload = {
        "identity_status": identity_status,
        "income_status": income_status,
        "liability_status": liability_status,
        "overall_status": overall_status,
        "comparisons": [c.model_dump() for c in comparisons],
    }
    step5_payload = {
        "income_metrics": income_calc,
        "obligation_metrics": obligation_calc,
        "statement_validation": statement_calc,
        "eligibility_result": eligibility_calc,
        "foir_assessment": {
            "foir_percentage": obligation_calc["foir_percentage"],
            "applicable_threshold": obligation_calc.get("applicable_foir_threshold", 50.0),
            "foir_zone": foir_zone,
            "foir_breach_severity": foir_breach_severity,
            "foir_headroom": obligation_calc.get("foir_headroom", 0.0),
            "max_eligible_emi": obligation_calc.get("max_eligible_emi", 0.0),
            "emi_affordability_passed": obligation_calc.get("emi_affordability_passed", True),
        },
    }
    step6_payload = {
        "risk_score": final_score,
        "risk_grade": risk_level,
        "routing_color": routing_color,
        "routing_reason": routing_reason,
        "factor_breakdown": factor_breakdown,
        "anomalies": [a.model_dump() for a in anomalies],
        "reviewer_checklist": checklist,
        "counterfactual_note": counterfactual,
    }

    return DecisionResult(
        application_id=application_id,
        overall_status=overall_status,
        identity_status=identity_status,
        income_status=income_status,
        liability_status=liability_status,
        declared_monthly_net=declared_net,
        verified_monthly_net=income_calc["effective_verified_income"],
        income_difference_percent=inc_diff_pct,
        declared_emi=obligation_calc["declared_emi"],
        detected_emi=obligation_calc["detected_emi"],
        dti_percent=dti_pct,
        foir_percentage=obligation_calc["foir_percentage"],
        foir_zone=foir_zone,
        foir_breach_severity=foir_breach_severity,
        applicable_foir_threshold=obligation_calc.get("applicable_foir_threshold", 50.0),
        max_eligible_emi=obligation_calc.get("max_eligible_emi", 0.0),
        emi_affordability_passed=obligation_calc.get("emi_affordability_passed", True),
        risk_score=int(final_score),
        risk_level=risk_level,
        recommendation=recommendation,
        routing_color=routing_color,
        routing_reason=routing_reason,
        requires_human_signoff=True,
        disposable_income=obligation_calc["disposable_income"],
        total_existing_emis=obligation_calc["total_existing_emis"],
        proposed_emi=obligation_calc["proposed_emi"],
        statement_arithmetic_status=statement_calc["status"],
        statement_arithmetic_difference=statement_calc["difference_amount"],
        eligibility_passed=eligibility_calc["passed"],
        eligibility_reasons=eligibility_calc["reasons"],
        factor_breakdown=factor_breakdown,
        reviewer_checklist=checklist,
        counterfactual_note=counterfactual,
        step4_comparison=step4_payload,
        step5_calculation=step5_payload,
        step6_risk_anomaly=step6_payload,
        discrepancies=comparisons,
        anomalies=anomalies,
        risk_factors=risk_factors,
        audit_notes=audit_notes,
    )