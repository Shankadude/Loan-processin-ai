from typing import Any, Dict, List


def get_doc(payload: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
    for doc in payload.get("documents", []):
        if doc.get("doc_type") == doc_type:
            return doc.get("extracted", {}) or {}
    return {}


def get_docs(payload: Dict[str, Any], doc_type: str) -> List[Dict[str, Any]]:
    return [
        doc.get("extracted", {}) or {}
        for doc in payload.get("documents", [])
        if doc.get("doc_type") == doc_type
    ]


def extract_declared(payload: Dict[str, Any]) -> Dict[str, Any]:
    loan = get_doc(payload, "LOAN_APPLICATION")
    return {
        "name": loan.get("name"),
        "dob": loan.get("dob"),
        "employer": loan.get("employer"),
        "gross_monthly": loan.get("gross_monthly"),
        "net_monthly": loan.get("net_monthly"),
        "loan_amount_requested": loan.get("loan_amount_requested"),
        "tenure_months": loan.get("tenure_months"),
        "purpose": loan.get("purpose"),
        "liabilities": loan.get("liabilities", []),
    }


def extract_verified(payload: Dict[str, Any]) -> Dict[str, Any]:
    applicant = payload.get("applicant", {})
    pan = get_doc(payload, "PAN_CARD")
    aadhaar = get_doc(payload, "AADHAAR_CARD")
    payslips = get_docs(payload, "PAYSLIP")
    form16 = get_doc(payload, "FORM16")
    bank = get_doc(payload, "BANK_STATEMENT")

    # Average net pay from payslips
    verified_net = 0.0
    if payslips:
        values = [float(p.get("net_pay", 0) or 0) for p in payslips]
        verified_net = sum(values) / len(values) if values else 0.0

    # Average salary credit from bank statement
    salary_credits = [
        float(tx.get("amount", 0) or 0)
        for tx in bank.get("transactions", [])
        if tx.get("category") == "salary_credit" and float(tx.get("amount", 0) or 0) > 0
    ]
    avg_salary_credit = sum(salary_credits) / len(salary_credits) if salary_credits else 0.0

    employer_name = None
    if payslips and payslips[0].get("employer_name"):
        employer_name = payslips[0].get("employer_name")
    elif form16.get("employer_name"):
        employer_name = form16.get("employer_name")

    return {
        "name": pan.get("name") or aadhaar.get("name") or applicant.get("full_name"),
        "dob": pan.get("dob") or aadhaar.get("dob") or applicant.get("dob"),
        "pan_number": pan.get("pan_number") or applicant.get("pan_number"),
        "aadhaar_last4": aadhaar.get("aadhaar_last4") or applicant.get("aadhaar_last4"),
        "employer": employer_name,
        "payslip_net_monthly": verified_net,
        "bank_avg_salary_credit": avg_salary_credit,
        "form16_annual_gross": float(form16.get("annual_gross", 0) or 0),
    }


def extract_liabilities(payload: Dict[str, Any]) -> Dict[str, Any]:
    loan = get_doc(payload, "LOAN_APPLICATION")
    bank = get_doc(payload, "BANK_STATEMENT")

    declared_liabilities = loan.get("liabilities", []) or []
    emi_transactions = [
        tx for tx in bank.get("transactions", [])
        if tx.get("category") == "emi_debit"
    ]
    detected_emi = sum(abs(float(tx.get("amount", 0) or 0)) for tx in emi_transactions)

    return {
        "declared_liabilities": declared_liabilities,
        "emi_transactions": emi_transactions,
        "detected_emi": detected_emi,
    }