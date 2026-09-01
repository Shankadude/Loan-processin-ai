from typing import Dict, Any, List, Tuple
from src.schemas.decision_models import Anomaly, RiskFactor, DecisionResult, FieldComparison
from src.decision_engine.calculations import calculate_income_metrics, calculate_obligation_metrics
from src.decision_engine.policy_loader import load_policy

def score_application(
    application_id: str,
    declared_payload: Dict[str, Any],
    verified_payload: Dict[str, Any],
    liabilities_payload: Dict[str, Any],
    comparisons: List[FieldComparison],
    policy_name: str = "personal_loan"
) -> DecisionResult:
    policy = load_policy(policy_name)
    
    declared_net = float(declared_payload.get("net_monthly") or declared_payload.get("gross_monthly") or 0.0)
    verified_net = float(verified_payload.get("payslip_net_monthly") or 0.0)
    bank_avg_credit = float(verified_payload.get("bank_avg_salary_credit") or 0.0)
    
    income_calc = calculate_income_metrics(declared_net, verified_net, bank_avg_credit)
    
    detected_emi = float(liabilities_payload.get("detected_emi") or 0.0)
    declared_liabilities = liabilities_payload.get("declared_liabilities", [])
    obligation_calc = calculate_obligation_metrics(detected_emi, declared_liabilities, income_calc["effective_verified_income"])

    # 1. Detect Anomalies
    anomalies: List[Anomaly] = []
    
    # Check identity statuses
    id_comparisons = [c for c in comparisons if "name" in c.field or "identity" in c.field or c.field in ["dob", "pan_number"]]
    id_statuses = [c.status for c in id_comparisons]
    if "MISMATCH" in id_statuses:
        identity_status = "MISMATCH"
        anomalies.append(Anomaly(code="IDENTITY_MISMATCH", severity="HIGH", description="Declared ID differs from verified identity records.", source="comparison_engine"))
    elif "PARTIAL_MATCH" in id_statuses:
        identity_status = "PARTIAL_MATCH"
        anomalies.append(Anomaly(code="IDENTITY_PARTIAL_MATCH", severity="MEDIUM", description="Partial match in applicant identity fields.", source="comparison_engine"))
    else:
        identity_status = "MATCH" if id_statuses else "NOT_AVAILABLE"

    # Check income discrepancy
    income_diff_pct = income_calc["income_difference_percent"]
    income_rule_max = policy.get("income", {}).get("max_acceptable_variance_percent", 10.0)
    if income_diff_pct > income_rule_max:
        income_status = "MISMATCH"
        anomalies.append(Anomaly(code="INCOME_DISCREPANCY", severity="HIGH", description=f"Income variance ({income_diff_pct}%) exceeds policy limit ({income_rule_max}%).", source="calculation_engine"))
    elif income_diff_pct > 5.0:
        income_status = "PARTIAL_MATCH"
        anomalies.append(Anomaly(code="INCOME_PARTIAL_DISCREPANCY", severity="MEDIUM", description="Moderate variance in declared income.", source="calculation_engine"))
    else:
        income_status = "MATCH"

    # Check undisclosed obligations
    declared_emi = obligation_calc["declared_emi"]
    if detected_emi > declared_emi + policy.get("liabilities", {}).get("max_allowed_undisclosed_emi_gap", 2000.0):
        liability_status = "MISMATCH"
        anomalies.append(Anomaly(code="UNDISCLOSED_LIABILITY", severity="HIGH", description=f"Detected EMI (₹{detected_emi:,.2f}) exceeds declared obligations (₹{declared_emi:,.2f}).", source="bank_analysis"))
    else:
        liability_status = "MATCH"

    # Check DTI
    dti_pct = obligation_calc["dti_percent"]
    dti_threshold = policy.get("foir", {}).get("standard_threshold_percent", 50.0)
    if dti_pct > dti_threshold:
        anomalies.append(Anomaly(code="HIGH_DTI", severity="HIGH", description=f"DTI ({dti_pct}%) exceeds standard lending threshold ({dti_threshold}%).", source="calculation_engine"))

    # 2. Risk Scoring & Deductions
    risk_score = 0
    risk_factors: List[RiskFactor] = []
    
    score_weights = {
        "IDENTITY_MISMATCH": 60,
        "INCOME_DISCREPANCY": 35,
        "INCOME_PARTIAL_DISCREPANCY": 15,
        "UNDISCLOSED_LIABILITY": 30,
        "HIGH_DTI": 35,
        "IDENTITY_PARTIAL_MATCH": 10
    }

    for anom in anomalies:
        weight = score_weights.get(anom.code, 10)
        risk_score += weight
        risk_factors.append(RiskFactor(factor=anom.code, score=weight, severity=anom.severity, reason=anom.description, source=anom.source))

    risk_score = min(risk_score, 100)

    # 3. Verdict
    if risk_score >= 60 or identity_status == "MISMATCH":
        risk_level = "HIGH"
        recommendation = "REJECT"
    elif risk_score >= 25 or income_status == "PARTIAL_MATCH":
        risk_level = "MEDIUM"
        recommendation = "REVIEW"
    else:
        risk_level = "LOW"
        recommendation = "AUTO_APPROVE"

    overall_status = "MISMATCH" if "MISMATCH" in [identity_status, income_status, liability_status] else ("PARTIAL_MATCH" if "PARTIAL_MATCH" in [identity_status, income_status, liability_status] else "MATCH")
    audit_notes = " ".join(rf.reason for rf in risk_factors) if risk_factors else "Clean application profile. Meets automated underwriting thresholds."

    return DecisionResult(
        application_id=application_id,
        overall_status=overall_status,
        identity_status=identity_status,
        income_status=income_status,
        liability_status=liability_status,
        declared_monthly_net=declared_net,
        verified_monthly_net=verified_net,
        income_difference_percent=income_diff_pct,
        declared_emi=declared_emi,
        detected_emi=detected_emi,
        dti_percent=dti_pct,
        risk_score=risk_score,
        risk_level=risk_level,
        recommendation=recommendation,
        discrepancies=comparisons,
        anomalies=anomalies,
        risk_factors=risk_factors,
        audit_notes=audit_notes
    )