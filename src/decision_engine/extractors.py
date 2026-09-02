from typing import Any, Dict, List


def get_doc(payload: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
    for doc in payload.get("documents", []):
        d_type = (doc.get("doc_type") or doc.get("document_type") or "").upper()
        if d_type == doc_type.upper():
            return doc.get("extracted_data") or doc.get("extracted") or {}
    return {}


def get_docs(payload: Dict[str, Any], doc_type: str) -> List[Dict[str, Any]]:
    return [
        doc.get("extracted_data") or doc.get("extracted") or {}
        for doc in payload.get("documents", [])
        if (doc.get("doc_type") or doc.get("document_type") or "").upper() == doc_type.upper()
    ]


def extract_declared(payload: Dict[str, Any]) -> Dict[str, Any]:
    loan = get_doc(payload, "LOAN_APPLICATION")
    financials = payload.get("financials", {}).get("loan_request", {})
    return {
        "name": loan.get("name"),
        "dob": loan.get("dob"),
        "pan_number": loan.get("pan") or loan.get("pan_number"),
        "employer": loan.get("employer"),
        "gross_monthly": loan.get("gross_monthly") or financials.get("declared_net_monthly"),
        "net_monthly": loan.get("net_monthly") or financials.get("declared_net_monthly"),
        "loan_amount_requested": loan.get("loan_amount_requested") or financials.get("requested_amount"),
        "tenure_months": loan.get("tenure_months") or 12,
        "purpose": loan.get("purpose"),
        "liabilities": loan.get("liabilities", []),
    }


def extract_verified(payload: Dict[str, Any]) -> Dict[str, Any]:
    applicant = payload.get("applicant", {})
    pan = get_doc(payload, "PAN_CARD")
    aadhaar = get_doc(payload, "IDENTITY_PROOF") or get_doc(payload, "AADHAAR_CARD")
    payslips = get_docs(payload, "SALARY_SLIP") or get_docs(payload, "PAYSLIP")
    form16 = get_doc(payload, "FORM_16_OR_ITR") or get_doc(payload, "FORM16")
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
        "name": pan.get("full_name") or aadhaar.get("full_name") or applicant.get("full_name"),
        "dob": pan.get("dob") or aadhaar.get("dob") or applicant.get("dob"),
        "pan_number": pan.get("pan_number") or (payslips[0].get("pan_number") if payslips else None),
        "employer": employer_name,
        "payslip_net_monthly": verified_net,
        "bank_avg_salary_credit": avg_salary_credit,
        "form16_annual_gross": float(form16.get("annual_gross", 0.0) or 0.0),
    }


def extract_liabilities(payload: Dict[str, Any]) -> Dict[str, Any]:
    loan = get_doc(payload, "LOAN_APPLICATION")
    bank = get_doc(payload, "BANK_STATEMENT")

    declared_liabilities = loan.get("liabilities", []) or []
    if not declared_liabilities and loan.get("declared_total_emi"):
        declared_liabilities = [{"type": "Declared EMI", "monthly_emi": float(loan.get("declared_total_emi"))}]

    emi_transactions = [
        tx for tx in bank.get("transactions", [])
        if tx.get("category") == "emi_debit"
    ]
    
    # Calculate representative monthly EMI run-rate (group by loan identifier / narrative)
    loan_monthly_map = {}
    for tx in emi_transactions:
        narr = tx.get("narration") or "loan"
        amt = abs(float(tx.get("amount", 0.0) or 0.0))
        if amt > 0:
            # Group by narrative prefix to find recurring monthly debits
            key = narr.split("-")[0].strip() if "-" in narr else narr.strip()
            loan_monthly_map[key] = max(loan_monthly_map.get(key, 0.0), amt)

    detected_emi = sum(loan_monthly_map.values()) if loan_monthly_map else 0.0

    return {
        "declared_liabilities": declared_liabilities,
        "emi_transactions": emi_transactions,
        "detected_emi": detected_emi,
    }