from typing import Dict, Any, List

def calculate_income_metrics(declared_net: float, verified_net: float, bank_avg_credit: float = 0.0) -> Dict[str, Any]:
    declared_net = float(declared_net or 0.0)
    verified_net = float(verified_net or 0.0)
    bank_avg_credit = float(bank_avg_credit or 0.0)

    income_diff = abs(declared_net - verified_net)
    income_diff_pct = round((income_diff / declared_net * 100), 2) if declared_net > 0 else 0.0
    effective_income = verified_net if verified_net > 0 else bank_avg_credit

    return {
        "declared_monthly_net": declared_net,
        "verified_monthly_net": verified_net,
        "bank_avg_salary_credit": bank_avg_credit,
        "effective_verified_income": round(effective_income, 2),
        "income_difference": round(income_diff, 2),
        "income_difference_percent": income_diff_pct,
    }

def calculate_obligation_metrics(detected_emi: float, declared_liabilities: List[dict] = None, verified_monthly_net: float = 0.0) -> Dict[str, Any]:
    detected_emi = float(detected_emi or 0.0)
    verified_monthly_net = float(verified_monthly_net or 0.0)
    declared_liabilities = declared_liabilities or []

    declared_emi = sum(float(l.get("emi_amount", 0.0) or l.get("monthly_emi", 0.0) or 0.0) for l in declared_liabilities if isinstance(l, dict))
    dti_percent = round((detected_emi / verified_monthly_net * 100), 2) if verified_monthly_net > 0 else 0.0

    return {
        "declared_emi": round(declared_emi, 2),
        "detected_emi": round(detected_emi, 2),
        "declared_liability_count": len(declared_liabilities),
        "dti_percent": dti_percent,
        "dti_status": "LOW" if dti_percent <= 30 else ("MODERATE" if dti_percent <= 50 else "HIGH")
    }

def calculate_statement_metrics(bank_avg_credit: float = 0.0, detected_emi: float = 0.0) -> Dict[str, Any]:
    bank_avg_credit = float(bank_avg_credit or 0.0)
    detected_emi = float(detected_emi or 0.0)
    salary_to_emi_pct = round((detected_emi / bank_avg_credit * 100), 2) if bank_avg_credit > 0 else 0.0
    remaining_income = max(bank_avg_credit - detected_emi, 0.0)

    return {
        "salary_to_emi_percent": salary_to_emi_pct,
        "estimated_remaining_income": round(remaining_income, 2)
    }