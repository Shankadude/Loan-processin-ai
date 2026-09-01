from typing import Any, Dict, List

def get_doc(payload: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
    for doc in payload.get("documents", []):
        if (doc.get("doc_type") or doc.get("document_type")) == doc_type:
            return doc.get("extracted_data") or doc.get("extracted") or {}
    return {}

def get_docs(payload: Dict[str, Any], doc_type: str) -> List[Dict[str, Any]]:
    return [
        doc.get("extracted_data") or doc.get("extracted") or {}
        for doc in payload.get("documents", [])
        if (doc.get("doc_type") or doc.get("document_type")) == doc_type
    ]

def extract_declared(payload: Dict[str, Any]) -> Dict[str, Any]:
    loan = get_doc(payload, "LOAN_APPLICATION")
    financials = payload.get("financials", {}).get("loan_request", {})
    return {
        "name": loan.get("name"),
        "dob": loan.get("dob"),
        "employer": loan.get("employer"),
        "gross_monthly": loan.get("gross_monthly") or financials.get("declared_net_monthly"),
        "net_monthly": loan.get("net_monthly") or financials.get("declared_net_monthly"),
        "loan_amount_requested": loan.get("loan_amount_requested") or financials.get("requested_amount"),
        "tenure_months": loan.get("tenure_months"),
        "purpose": loan.get("purpose"),
        "liabilities": loan.get("liabilities", []),
    }

def extract_verified(payload: Dict[str, Any]) -> Dict[str, Any]:
    applicant = payload.get("applicant", {})
    pan = get_doc(payload, "PAN_CARD")
    aadhaar = get_doc(payload, "AADHAAR_CARD") or get_doc(payload, "IDENTITY_PROOF")
    payslips = get_docs(payload, "PAYSLIP") or get_docs(payload, "SALARY_SLIP")
    form16 = get_doc(payload, "FORM16") or get_doc(payload, "FORM_16_OR_ITR")
    bank = get_doc(payload, "BANK_STATEMENT")

    verified_net = 0.0
    if payslips:
        values = [float(p.get("net_pay", 0.0) or p.get("net_income", 0.0) or 0.0) for p in payslips]
        verified_net = sum(values) / len(values) if values else 0.0

    salary_credits = [
        float(tx.get("amount", 0.0) or 0.0)
        for tx in bank.get("transactions", [])
        if tx.get("category") == "salary_credit" and float(tx.get("amount", 0.0) or 0.0) > 0
    ]
    avg_salary_credit = sum(salary_credits) / len(salary_credits) if salary_credits else float(bank.get("total_monthly_salary_credits", 0.0) or 0.0)

    employer_name = None
    if payslips and payslips[0].get("employer_name"):
        employer_name = payslips[0].get("employer_name")
    elif form16.get("employer_name"):
        employer_name = form16.get("employer_name")

    return {
        "name": pan.get("full_name") or pan.get("name") or aadhaar.get("full_name") or aadhaar.get("name") or applicant.get("full_name"),
        "dob": pan.get("dob") or aadhaar.get("dob") or applicant.get("dob"),
        "pan_number": pan.get("pan_number") or applicant.get("pan_number"),
        "aadhaar_last4": aadhaar.get("aadhaar_last4") or applicant.get("aadhaar_last4"),
        "employer": employer_name,
        "payslip_net_monthly": verified_net,
        "bank_avg_salary_credit": avg_salary_credit,
        "form16_annual_gross": float(form16.get("annual_gross", 0.0) or form16.get("gross_total_income", 0.0) or 0.0),
    }

def extract_liabilities(payload: Dict[str, Any]) -> Dict[str, Any]:
    loan = get_doc(payload, "LOAN_APPLICATION")
    bank = get_doc(payload, "BANK_STATEMENT")

    declared_liabilities = loan.get("liabilities", []) or []
    emi_transactions = [
        tx for tx in bank.get("transactions", [])
        if tx.get("category") == "emi_debit"
    ]
    detected_emi = sum(abs(float(tx.get("amount", 0.0) or 0.0)) for tx in emi_transactions) or float(bank.get("total_recurring_emi_debits", 0.0) or 0.0)

    return {
        "declared_liabilities": declared_liabilities,
        "emi_transactions": emi_transactions,
        "detected_emi": detected_emi,
    }