from typing import Any, Dict, List, Optional
from src.schemas.decision_models import Anomaly, FieldComparison
from src.decision_engine.policy_loader import load_policy


def detect_discrepancies(
    comparisons: List[FieldComparison],
    income_calc: Dict[str, Any],
    obligation_calc: Dict[str, Any],
    statement_calc: Optional[Dict[str, Any]] = None,
    eligibility_calc: Optional[Dict[str, Any]] = None,
    policy_name: str = "personal_loan",
) -> List[Anomaly]:
    """
    Consolidates detected discrepancies from Step 4 (Document Comparison)
    and Step 5 (Calculations) into standardized Anomaly models with risk severity.
    """
    policy = load_policy(policy_name)
    income_policy = policy.get("income", {})
    foir_policy = policy.get("foir", {})
    liab_policy = policy.get("liabilities", {})

    max_inc_var = float(income_policy.get("max_acceptable_variance_percent", 10.0))
    severe_inc_var = float(income_policy.get("severe_variance_percent", 20.0))
    max_foir = float(foir_policy.get("standard_threshold_percent", 50.0))
    high_foir = float(foir_policy.get("high_risk_threshold_percent", 65.0))
    max_gap = float(liab_policy.get("max_allowed_undisclosed_emi_gap", 2000.0))
    major_gap = float(liab_policy.get("major_undisclosed_threshold", 10000.0))

    anomalies: List[Anomaly] = []

    # 1. Identity & Cross-Document Checks from Step 4
    for c in comparisons:
        if c.status == "MISMATCH":
            sev = "HIGH" if ("name" in c.field or "pan" in c.field or "identity" in c.field) else "MEDIUM"
            anomalies.append(
                Anomaly(
                    code=f"{c.field.upper()}_MISMATCH",
                    severity=sev,
                    description=c.reason or f"Mismatch detected in {c.field}: declared '{c.declared_value}' vs verified '{c.verified_value}'.",
                    source="document_comparison",
                    evidence={
                        "field": c.field,
                        "declared": c.declared_value,
                        "verified": c.verified_value,
                    },
                )
            )
        elif c.status == "PARTIAL_MATCH":
            anomalies.append(
                Anomaly(
                    code=f"{c.field.upper()}_PARTIAL_MATCH",
                    severity="MEDIUM",
                    description=c.reason or f"Partial match in {c.field}: '{c.declared_value}' vs '{c.verified_value}'.",
                    source="document_comparison",
                    evidence={
                        "field": c.field,
                        "declared": c.declared_value,
                        "verified": c.verified_value,
                    },
                )
            )

    # 2. Income Discrepancies
    inc_var_pct = float(income_calc.get("income_difference_percent", 0.0))
    inc_diff_amt = float(income_calc.get("income_difference", 0.0))
    if inc_var_pct > severe_inc_var:
        anomalies.append(
            Anomaly(
                code="SEVERE_INCOME_DISCREPANCY",
                severity="HIGH",
                description=f"Severe income variance of {inc_var_pct}% (Rs. {inc_diff_amt:,.2f}) exceeds policy tolerance ({max_inc_var}%).",
                source="income_calculation",
                evidence={"variance_percent": inc_var_pct, "variance_amount": inc_diff_amt},
            )
        )
    elif inc_var_pct > max_inc_var:
        anomalies.append(
            Anomaly(
                code="INCOME_DISCREPANCY",
                severity="MEDIUM",
                description=f"Income variance of {inc_var_pct}% (Rs. {inc_diff_amt:,.2f}) exceeds policy standard ({max_inc_var}%).",
                source="income_calculation",
                evidence={"variance_percent": inc_var_pct, "variance_amount": inc_diff_amt},
            )
        )

    # 3. Undisclosed Liabilities & Debt Stacking
    gap = float(obligation_calc.get("undisclosed_liability_gap", 0.0))
    detected_emi = float(obligation_calc.get("detected_emi", 0.0))
    declared_emi = float(obligation_calc.get("declared_emi", 0.0))
    if gap > major_gap:
        anomalies.append(
            Anomaly(
                code="MAJOR_UNDISCLOSED_LIABILITY",
                severity="HIGH",
                description=f"Major undisclosed loan debt: detected bank EMI (Rs. {detected_emi:,.2f}) exceeds declared obligations (Rs. {declared_emi:,.2f}) by Rs. {gap:,.2f}.",
                source="bank_transaction_analysis",
                evidence={"detected_emi": detected_emi, "declared_emi": declared_emi, "gap": gap},
            )
        )
    elif gap > max_gap or obligation_calc.get("has_undisclosed_liabilities"):
        anomalies.append(
            Anomaly(
                code="UNDISCLOSED_LIABILITY",
                severity="MEDIUM",
                description=f"Undisclosed loan EMI gap of Rs. {gap:,.2f} detected from bank statement debits.",
                source="bank_transaction_analysis",
                evidence={"detected_emi": detected_emi, "declared_emi": declared_emi, "gap": gap},
            )
        )

    # 4. Excessive FOIR / DTI Overleveraging (Income-Slab-Aware)
    dti_pct = float(obligation_calc.get("dti_percent", 0.0))
    foir_zone = obligation_calc.get("foir_zone", "SAFE")
    foir_breach = obligation_calc.get("foir_breach", False)
    applicable_threshold = float(obligation_calc.get("applicable_foir_threshold", max_foir))
    foir_headroom = float(obligation_calc.get("foir_headroom", 0.0))
    max_eligible_emi = float(obligation_calc.get("max_eligible_emi", 0.0))

    if foir_zone == "CRITICAL" or dti_pct > high_foir:
        anomalies.append(
            Anomaly(
                code="CRITICAL_HIGH_DTI",
                severity="HIGH",
                description=(
                    f"Critically high DTI / FOIR ({dti_pct:.1f}%) exceeds absolute risk ceiling ({high_foir:.0f}%). "
                    f"Income-slab threshold: {applicable_threshold:.0f}%, max eligible EMI: Rs. {max_eligible_emi:,.2f}."
                ),
                source="obligation_calculation",
                evidence={
                    "dti_percent": dti_pct,
                    "foir_zone": foir_zone,
                    "threshold": high_foir,
                    "applicable_threshold": applicable_threshold,
                    "max_eligible_emi": max_eligible_emi,
                },
            )
        )
    elif foir_breach or foir_zone == "BREACH" or dti_pct > applicable_threshold:
        anomalies.append(
            Anomaly(
                code="HIGH_DTI",
                severity="MEDIUM",
                description=(
                    f"DTI / FOIR ({dti_pct:.1f}%) exceeds income-slab lending threshold ({applicable_threshold:.0f}%) — "
                    f"zone: {foir_zone}, headroom: {foir_headroom:.1f}%. Max eligible EMI: Rs. {max_eligible_emi:,.2f}."
                ),
                source="obligation_calculation",
                evidence={
                    "dti_percent": dti_pct,
                    "foir_zone": foir_zone,
                    "threshold": applicable_threshold,
                    "applicable_threshold": applicable_threshold,
                    "foir_headroom": foir_headroom,
                    "max_eligible_emi": max_eligible_emi,
                },
            )
        )

    # 4b. EMI Unaffordability Detection
    emi_affordable = obligation_calc.get("emi_affordability_passed", True)
    proposed_emi = float(obligation_calc.get("proposed_emi", 0.0))
    if not emi_affordable and proposed_emi > 0:
        anomalies.append(
            Anomaly(
                code="EMI_UNAFFORDABLE",
                severity="HIGH",
                description=(
                    f"Proposed EMI (Rs. {proposed_emi:,.2f}) exceeds maximum eligible EMI "
                    f"(Rs. {max_eligible_emi:,.2f}) per income-slab FOIR capacity. "
                    f"Applicant cannot service this loan at current obligations."
                ),
                source="foir_assessment",
                evidence={
                    "proposed_emi": proposed_emi,
                    "max_eligible_emi": max_eligible_emi,
                    "foir_percentage": dti_pct,
                    "applicable_threshold": applicable_threshold,
                },
            )
        )

    # 5. Bank Statement Balance Reconciliation (Tampering / Alteration Detection)
    if statement_calc and statement_calc.get("status") == "MISMATCH":
        diff = float(statement_calc.get("difference_amount", 0.0))
        anomalies.append(
            Anomaly(
                code="STATEMENT_ARITHMETIC_MISMATCH",
                severity="HIGH",
                description=statement_calc.get("message") or f"Bank statement arithmetic mismatch of Rs. {diff:,.2f}. Stated closing does not reconcile with debits/credits.",
                source="statement_reconciliation",
                evidence={"difference_amount": diff},
            )
        )

    # 6. Policy Eligibility Failures
    if eligibility_calc and not eligibility_calc.get("passed", True):
        for reason in eligibility_calc.get("reasons", []):
            anomalies.append(
                Anomaly(
                    code="POLICY_ELIGIBILITY_FAILURE",
                    severity="HIGH",
                    description=reason,
                    source="policy_engine",
                    evidence={"policy_reason": reason},
                )
            )

    return anomalies
