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


def calculate_obligation_metrics(
    detected_emi: float = 0.0,
    declared_liabilities: Optional[List[dict]] = None,
    verified_monthly_net: float = 0.0,
    bank_transactions: Optional[List[dict]] = None,
    proposed_emi: float = 0.0,
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

    # 4. Total Obligations & FOIR / DTI
    total_existing_emis = max(declared_emi, detected_emi)
    total_obligations = round(total_existing_emis + proposed_emi, 2)
    dti_percent = round((total_obligations / verified_monthly_net * 100), 2) if verified_monthly_net > 0 else 0.0
    disposable_income = max(round(verified_monthly_net - total_obligations, 2), 0.0)

    return {
        "declared_emi": round(declared_emi, 2),
        "detected_emi": round(detected_emi, 2),
        "declared_liability_count": len(declared_liabilities),
        "undisclosed_liability_gap": undisclosed_gap,
        "has_undisclosed_liabilities": has_undisclosed,
        "total_existing_emis": round(total_existing_emis, 2),
        "proposed_emi": round(proposed_emi, 2),
        "total_monthly_obligations": total_obligations,
        "dti_percent": dti_percent,
        "foir_percentage": dti_percent,
        "disposable_income": disposable_income,
        "dti_status": "LOW" if dti_percent <= 30 else ("MODERATE" if dti_percent <= 50 else "HIGH"),
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
    policy_name: str = "personal_loan",
) -> Dict[str, Any]:
    """
    Evaluates applicant against lender credit underwriting rules.
    """
    policy = load_policy(policy_name)
    income_rule = policy.get("income", {})
    foir_rule = policy.get("foir", {})
    liab_rule = policy.get("liabilities", {})

    min_income = float(income_rule.get("min_monthly_net_income", 25000.0))
    max_variance = float(income_rule.get("max_acceptable_variance_percent", 10.0))
    max_foir = float(foir_rule.get("standard_threshold_percent", 50.0))
    max_gap = float(liab_rule.get("max_allowed_undisclosed_emi_gap", 2000.0))

    reasons = []

    if verified_income < min_income:
        reasons.append(f"Verified income (Rs. {verified_income:,.2f}) is below policy minimum (Rs. {min_income:,.2f})")

    if foir_percentage > max_foir:
        reasons.append(f"FOIR/DTI ({foir_percentage:.1f}%) exceeds maximum policy threshold ({max_foir:.1f}%)")

    if income_variance_percent > max_variance:
        reasons.append(f"Income variance ({income_variance_percent:.1f}%) exceeds acceptable tolerance ({max_variance:.1f}%)")

    if undisclosed_liability_gap > max_gap:
        reasons.append(f"Undisclosed EMI gap (Rs. {undisclosed_liability_gap:,.2f}) exceeds policy limit (Rs. {max_gap:,.2f})")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "reasons": reasons if reasons else ["Meets all standard credit underwriting eligibility criteria."],
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