from typing import Dict, Any, List, Optional
from src.decision_engine.policy_loader import load_policy


def calculate_income_metrics(
    declared_net: float,
    verified_net: float = 0.0,
    bank_avg_credit: float = 0.0,
    payslips: Optional[List[dict]] = None,
    bank_transactions: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    declared_net = float(declared_net or 0.0)
    verified_net = float(verified_net or 0.0)
    bank_avg_credit = float(bank_avg_credit or 0.0)

    # 1. Parse Payslip Averages if payslip objects provided
    if payslips:
        ps_vals = []
        for p in payslips:
            ext = p.get("extracted_data") or p.get("extracted") or p
            val = ext.get("net_pay") or ext.get("net_income") or ext.get("net_salary")
            if val is not None:
                try:
                    ps_vals.append(float(val))
                except (ValueError, TypeError):
                    pass
        if ps_vals:
            verified_net = sum(ps_vals) / len(ps_vals)

    # 2. Parse Salary Credits from Bank Transactions if provided
    if bank_transactions:
        credits = []
        for tx in bank_transactions:
            cat = (tx.get("category") or "").lower()
            amt = float(tx.get("amount") or 0.0)
            if "salary" in cat and amt > 0:
                credits.append(amt)
        if credits:
            bank_avg_credit = sum(credits) / len(credits)

    # 3. Conservative Verified Income Resolution
    if verified_net > 0 and bank_avg_credit > 0:
        effective_income = min(verified_net, bank_avg_credit)
    elif verified_net > 0:
        effective_income = verified_net
    elif bank_avg_credit > 0:
        effective_income = bank_avg_credit
    else:
        effective_income = declared_net

    income_diff = abs(declared_net - effective_income)
    income_diff_pct = round((income_diff / declared_net * 100), 2) if declared_net > 0 else 0.0

    return {
        "declared_monthly_net": declared_net,
        "verified_monthly_net": round(verified_net, 2),
        "bank_avg_salary_credit": round(bank_avg_credit, 2),
        "effective_verified_income": round(effective_income, 2),
        "income_difference": round(income_diff, 2),
        "income_difference_percent": income_diff_pct,
    }


# ---------------------------------------------------------------------------
# FOIR (Fixed Obligation to Income Ratio) Assessment Engine
# ---------------------------------------------------------------------------
# Industry-standard FOIR calculation per RBI / NBFC norms:
#
#   FOIR % = (Total Monthly Obligations / Verified Monthly Income) × 100
#
#   where Total Monthly Obligations = Existing EMIs + Proposed EMI
#
#   The applicable FOIR threshold varies by income slab:
#     Income ≤ ₹25,000     → max 40%
#     ₹25,001 – ₹50,000    → max 50%
#     ₹50,001 – ₹1,00,000  → max 55%
#     > ₹1,00,000           → max 60%
#
#   Max Eligible EMI = (Verified Income × Applicable Threshold / 100)
#                      − Existing EMIs
#
#   FOIR Zones:
#     SAFE     → FOIR ≤ (applicable_threshold − buffer)
#     STRETCH  → (applicable_threshold − buffer) < FOIR ≤ applicable_threshold
#     BREACH   → applicable_threshold < FOIR ≤ high_risk_threshold (65%)
#     CRITICAL → FOIR > high_risk_threshold (65%)
# ---------------------------------------------------------------------------


def _get_applicable_foir_threshold(
    verified_income: float,
    policy: Dict[str, Any],
) -> float:
    """
    Returns the income-slab-based FOIR threshold for the applicant.
    Falls back to the flat standard_threshold_percent if slabs are not defined.
    """
    foir_rule = policy.get("foir", {})
    slabs = foir_rule.get("income_slab_thresholds", [])

    if not slabs:
        return float(foir_rule.get("standard_threshold_percent", 50.0))

    for slab in slabs:
        min_inc = float(slab.get("min_income", 0))
        max_inc = float(slab.get("max_income", 999999999))
        if min_inc <= verified_income <= max_inc:
            return float(slab.get("max_foir_percent", 50.0))

    # Fallback: use the flat threshold if no slab matched
    return float(foir_rule.get("standard_threshold_percent", 50.0))


def _classify_foir_zone(
    foir_pct: float,
    applicable_threshold: float,
    buffer_pct: float,
    high_risk_pct: float,
) -> str:
    """
    Classifies the FOIR into one of four zones:
      SAFE     → FOIR ≤ (threshold − buffer)
      STRETCH  → (threshold − buffer) < FOIR ≤ threshold
      BREACH   → threshold < FOIR ≤ high_risk_threshold
      CRITICAL → FOIR > high_risk_threshold
    """
    safe_ceiling = applicable_threshold - buffer_pct

    if foir_pct <= safe_ceiling:
        return "SAFE"
    elif foir_pct <= applicable_threshold:
        return "STRETCH"
    elif foir_pct <= high_risk_pct:
        return "BREACH"
    else:
        return "CRITICAL"


def _classify_foir_breach_severity(foir_zone: str) -> str:
    """
    Maps FOIR zone to breach severity for risk scoring deductions.
      SAFE     → none
      STRETCH  → marginal
      BREACH   → moderate
      CRITICAL → severe
    """
    return {
        "SAFE": "none",
        "STRETCH": "marginal",
        "BREACH": "moderate",
        "CRITICAL": "severe",
    }.get(foir_zone, "none")


def calculate_foir_assessment(
    verified_monthly_income: float,
    total_existing_emis: float,
    proposed_emi: float,
    policy_name: str = "personal_loan",
) -> Dict[str, Any]:
    """
    Comprehensive FOIR (Fixed Obligation to Income Ratio) assessment.

    Inputs:
        verified_monthly_income : Conservatively resolved monthly income
        total_existing_emis     : max(declared EMIs, detected bank EMIs)
        proposed_emi            : EMI for the requested loan
        policy_name             : Policy ruleset to load

    Returns a dict with:
        foir_percentage          – Computed FOIR %
        applicable_foir_threshold – Income-slab-based max FOIR %
        foir_breach              – True if FOIR > applicable threshold
        foir_breach_severity     – none / marginal / moderate / severe
        foir_zone                – SAFE / STRETCH / BREACH / CRITICAL
        foir_headroom            – (threshold − FOIR); negative means breach
        max_eligible_emi         – Maximum EMI the applicant can afford per policy
        emi_affordability_passed – True if proposed EMI ≤ max eligible EMI
        total_monthly_obligations – All obligations summed
        disposable_income        – Income remaining after all obligations
    """
    policy = load_policy(policy_name)
    foir_rule = policy.get("foir", {})

    verified_income = float(verified_monthly_income or 0.0)
    existing_emis = float(total_existing_emis or 0.0)
    prop_emi = float(proposed_emi or 0.0)

    # --- FOIR Policy Parameters ---
    applicable_threshold = _get_applicable_foir_threshold(verified_income, policy)
    high_risk = float(foir_rule.get("high_risk_threshold_percent", 65.0))
    buffer = float(foir_rule.get("emi_affordability_buffer_percent", 5.0))

    # --- Core FOIR Computation ---
    # FOIR % = (Existing EMIs + Proposed EMI) / Verified Income × 100
    total_obligations = round(existing_emis + prop_emi, 2)

    if verified_income > 0:
        foir_pct = round((total_obligations / verified_income) * 100, 2)
    else:
        foir_pct = 100.0  # No income means maximum risk

    # --- Zone & Breach Classification ---
    foir_zone = _classify_foir_zone(foir_pct, applicable_threshold, buffer, high_risk)
    foir_breach = foir_pct > applicable_threshold
    breach_severity = _classify_foir_breach_severity(foir_zone)

    # --- Headroom (positive = room to spare, negative = over threshold) ---
    foir_headroom = round(applicable_threshold - foir_pct, 2)

    # --- Max Eligible EMI Calculation ---
    # Max EMI = (Income × Applicable Threshold / 100) − Existing EMIs
    if verified_income > 0:
        max_emi_capacity = round((verified_income * applicable_threshold / 100.0), 2)
        max_eligible_emi = round(max(0.0, max_emi_capacity - existing_emis), 2)
    else:
        max_eligible_emi = 0.0

    emi_affordability_passed = prop_emi <= max_eligible_emi

    # --- Disposable Income ---
    disposable_income = round(max(0.0, verified_income - total_obligations), 2)

    return {
        "foir_percentage": foir_pct,
        "applicable_foir_threshold": applicable_threshold,
        "foir_breach": foir_breach,
        "foir_breach_severity": breach_severity,
        "foir_zone": foir_zone,
        "foir_headroom": foir_headroom,
        "max_eligible_emi": max_eligible_emi,
        "emi_affordability_passed": emi_affordability_passed,
        "total_monthly_obligations": total_obligations,
        "existing_emis": existing_emis,
        "proposed_emi": prop_emi,
        "disposable_income": disposable_income,
        "verified_income_used": verified_income,
    }





def calculate_obligation_metrics(
    detected_emi: float = 0.0,
    declared_liabilities: Optional[List[dict]] = None,
    verified_monthly_net: float = 0.0,
    bank_transactions: Optional[List[dict]] = None,
    proposed_emi: float = 0.0,
    policy_name: str = "personal_loan",
) -> Dict[str, Any]:
    detected_emi = float(detected_emi or 0.0)
    verified_monthly_net = float(verified_monthly_net or 0.0)
    declared_liabilities = declared_liabilities or []
    proposed_emi = float(proposed_emi or 0.0)

    # 1. Sum Declared EMIs
    declared_emi = sum(
        float(l.get("emi_amount", 0.0) or l.get("monthly_emi", 0.0) or 0.0)
        for l in declared_liabilities
        if isinstance(l, dict)
    )

    # 2. Scan Bank Transactions for recurring EMI Debits (Representative Monthly Run-Rate)
    if bank_transactions:
        loan_monthly_map = {}
        for tx in bank_transactions:
            cat = (tx.get("category") or "").lower()
            narr = (tx.get("narration") or tx.get("description") or "loan").lower()
            amt = abs(float(tx.get("amount") or 0.0))
            if ("emi" in cat or "loan" in cat) and amt > 0:
                key = narr.split("-")[0].strip() if "-" in narr else narr.strip()
                loan_monthly_map[key] = max(loan_monthly_map.get(key, 0.0), amt)
        if loan_monthly_map:
            detected_emi = sum(loan_monthly_map.values())

    # 3. Undisclosed Debt
    undisclosed_gap = max(round(detected_emi - declared_emi, 2), 0.0)
    has_undisclosed = undisclosed_gap > 2000.0

    # 4. Total Obligations (before FOIR assessment)
    total_existing_emis = max(declared_emi, detected_emi)

    # 5. FOIR Assessment (Income-Slab-Aware)
    foir_result = calculate_foir_assessment(
        verified_monthly_income=verified_monthly_net,
        total_existing_emis=total_existing_emis,
        proposed_emi=proposed_emi,
        policy_name=policy_name,
    )

    # 7. Backward-compatible fields
    total_obligations = foir_result["total_monthly_obligations"]
    foir_pct = foir_result["foir_percentage"]
    disposable_income = foir_result["disposable_income"]

    # Simple DTI status label (backward-compatible)
    dti_status = "LOW" if foir_pct <= 30 else ("MODERATE" if foir_pct <= 50 else "HIGH")

    return {
        # --- Existing Fields (Backward Compatible) ---
        "declared_emi": round(declared_emi, 2),
        "detected_emi": round(detected_emi, 2),
        "declared_liability_count": len(declared_liabilities),
        "undisclosed_liability_gap": undisclosed_gap,
        "has_undisclosed_liabilities": has_undisclosed,
        "total_existing_emis": round(total_existing_emis, 2),
        "proposed_emi": round(proposed_emi, 2),
        "total_monthly_obligations": total_obligations,
        "dti_percent": foir_pct,
        "foir_percentage": foir_pct,
        "disposable_income": disposable_income,
        "dti_status": dti_status,

        # --- New FOIR Assessment Fields ---
        "applicable_foir_threshold": foir_result["applicable_foir_threshold"],
        "foir_breach": foir_result["foir_breach"],
        "foir_breach_severity": foir_result["foir_breach_severity"],
        "foir_zone": foir_result["foir_zone"],
        "foir_headroom": foir_result["foir_headroom"],
        "max_eligible_emi": foir_result["max_eligible_emi"],
        "emi_affordability_passed": foir_result["emi_affordability_passed"],
    }


def validate_statement_arithmetic(
    opening_balance: Optional[float] = None,
    total_credits: Optional[float] = None,
    total_debits: Optional[float] = None,
    closing_balance: Optional[float] = None,
    max_error: float = 5.0,
) -> Dict[str, Any]:
    """
    Verifies the accounting balance identity:
    Opening Balance + Total Credits - Total Debits == Closing Balance
    Detects tampered or forged bank statement PDFs.
    """
    if None in (opening_balance, total_credits, total_debits, closing_balance):
        return {
            "is_valid": True,
            "status": "NOT_AVAILABLE",
            "expected_closing_balance": 0.0,
            "actual_closing_balance": 0.0,
            "difference_amount": 0.0,
            "message": "Bank statement balance figures not present for arithmetic validation.",
        }

    op = float(opening_balance)
    cr = float(total_credits)
    db = float(total_debits)
    cl = float(closing_balance)

    expected_cl = round(op + cr - db, 2)
    diff = round(abs(expected_cl - cl), 2)

    if diff <= max_error:
        return {
            "is_valid": True,
            "status": "MATCH",
            "expected_closing_balance": expected_cl,
            "actual_closing_balance": cl,
            "difference_amount": diff,
            "message": f"Bank statement arithmetic verified: Op (Rs. {op:,.2f}) + Cr (Rs. {cr:,.2f}) - Db (Rs. {db:,.2f}) == Cl (Rs. {cl:,.2f}).",
        }
    else:
        return {
            "is_valid": False,
            "status": "MISMATCH",
            "expected_closing_balance": expected_cl,
            "actual_closing_balance": cl,
            "difference_amount": diff,
            "message": f"Arithmetic discrepancy of Rs. {diff:,.2f} detected between calculated balance (Rs. {expected_cl:,.2f}) and stated closing (Rs. {cl:,.2f}). Potential statement tampering.",
        }


def check_eligibility(
    verified_income: float,
    foir_percentage: float,
    income_variance_percent: float,
    undisclosed_liability_gap: float = 0.0,
    foir_zone: str = "SAFE",
    emi_affordability_passed: bool = True,
    applicable_foir_threshold: float = 50.0,
    max_eligible_emi: float = 0.0,
    proposed_emi: float = 0.0,
    policy_name: str = "personal_loan",
) -> Dict[str, Any]:
    """
    Evaluates applicant against lender credit underwriting rules.
    Now includes income-slab-aware FOIR evaluation and EMI affordability checks.
    """
    policy = load_policy(policy_name)
    income_rule = policy.get("income", {})
    foir_rule = policy.get("foir", {})
    liab_rule = policy.get("liabilities", {})

    min_income = float(income_rule.get("min_monthly_net_income", 25000.0))
    max_variance = float(income_rule.get("max_acceptable_variance_percent", 10.0))
    max_gap = float(liab_rule.get("max_allowed_undisclosed_emi_gap", 2000.0))
    high_risk_foir = float(foir_rule.get("high_risk_threshold_percent", 65.0))

    reasons = []

    # 1. Minimum Income Check
    if verified_income < min_income:
        reasons.append(f"Verified income (Rs. {verified_income:,.2f}) is below policy minimum (Rs. {min_income:,.2f})")

    # 2. FOIR Check — Income-Slab-Aware
    #    Uses the applicable_foir_threshold from the income slab, not a flat 50%
    if foir_percentage > applicable_foir_threshold:
        reasons.append(
            f"FOIR ({foir_percentage:.1f}%) exceeds income-slab threshold "
            f"({applicable_foir_threshold:.1f}%) — Zone: {foir_zone}"
        )

    # 3. Hard Reject — FOIR above absolute high-risk ceiling
    if foir_percentage > high_risk_foir:
        reasons.append(
            f"FOIR ({foir_percentage:.1f}%) exceeds absolute high-risk ceiling "
            f"({high_risk_foir:.1f}%) — CRITICAL overleveraging"
        )

    # 4. EMI Affordability Check
    if proposed_emi > 0 and not emi_affordability_passed:
        reasons.append(
            f"Proposed EMI (Rs. {proposed_emi:,.2f}) exceeds maximum eligible EMI "
            f"(Rs. {max_eligible_emi:,.2f}) per income-slab FOIR capacity"
        )

    # 5. Income Variance Check
    if income_variance_percent > max_variance:
        reasons.append(f"Income variance ({income_variance_percent:.1f}%) exceeds acceptable tolerance ({max_variance:.1f}%)")

    # 6. Undisclosed Liability Check
    if undisclosed_liability_gap > max_gap:
        reasons.append(f"Undisclosed EMI gap (Rs. {undisclosed_liability_gap:,.2f}) exceeds policy limit (Rs. {max_gap:,.2f})")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "reasons": reasons if reasons else ["Meets all standard credit underwriting eligibility criteria."],
        "foir_zone": foir_zone,
        "applicable_foir_threshold": applicable_foir_threshold,
    }


def calculate_statement_metrics(bank_avg_credit: float = 0.0, detected_emi: float = 0.0) -> Dict[str, Any]:
    bank_avg_credit = float(bank_avg_credit or 0.0)
    detected_emi = float(detected_emi or 0.0)
    salary_to_emi_pct = round((detected_emi / bank_avg_credit * 100), 2) if bank_avg_credit > 0 else 0.0
    remaining_income = max(bank_avg_credit - detected_emi, 0.0)

    return {
        "salary_to_emi_percent": salary_to_emi_pct,
        "estimated_remaining_income": round(remaining_income, 2),
    }