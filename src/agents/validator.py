import difflib
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class ValidationReport(BaseModel):
    name_check_passed: bool
    name_discrepancies: List[str] = Field(default_factory=list)
    income_variance_pct: float = Field(default=0.0, description="Variance between payslip and bank deposits")
    calculated_dti: float = Field(default=0.0, description="Debt-to-Income ratio in percentage")
    dti_risk_level: str = Field(default="LOW", description="LOW, MODERATE, or HIGH")
    critical_flags: List[str] = Field(default_factory=list)
    validation_status: str = Field(default="PASSED", description="PASSED, FLAGGED, or FAILED")

def are_names_similar(name1: str, name2: str, threshold: float = 0.75) -> bool:
    """Fuzzy compares two names to handle minor spelling variations or ordering."""
    if not name1 or not name2:
        return False
    n1 = " ".join(sorted(name1.strip().lower().split()))
    n2 = " ".join(sorted(name2.strip().lower().split()))
    similarity = difflib.SequenceMatcher(None, n1, n2).ratio()
    return similarity >= threshold

def validate_application_data(
    kyc_data: List[Dict[str, Any]],
    salary_slips: List[Dict[str, Any]],
    tax_forms: List[Dict[str, Any]],
    bank_statements: List[Dict[str, Any]]
) -> ValidationReport:
    """Executes deterministic cross-verification across all extracted documents."""
    critical_flags: List[str] = []
    name_discrepancies: List[str] = []

    # 1. Collect all names across documents
    extracted_names = []
    for kyc in kyc_data:
        if kyc.get("full_name"):
            extracted_names.append((kyc.get("full_name"), "KYC Document"))
    for slip in salary_slips:
        if slip.get("employee_name"):
            extracted_names.append((slip.get("employee_name"), "Salary Slip"))
    for tax in tax_forms:
        if tax.get("taxpayer_name"):
            extracted_names.append((tax.get("taxpayer_name"), "Tax Form"))
    for bank in bank_statements:
        if bank.get("account_holder_name"):
            extracted_names.append((bank.get("account_holder_name"), "Bank Statement"))

    # Name consistency check
    name_check_passed = True
    if len(extracted_names) > 1:
        primary_name, primary_src = extracted_names[0]
        for name, src in extracted_names[1:]:
            if not are_names_similar(primary_name, name):
                name_check_passed = False
                name_discrepancies.append(
                    f"Name mismatch: '{primary_name}' ({primary_src}) vs '{name}' ({src})"
                )

    if not name_check_passed:
        critical_flags.append("Borrower name inconsistency detected across documentation.")

    # 2. Income & Bank Deposit Cross-Verification
    gross_income = 0.0
    if salary_slips:
        gross_income = max(s.get("gross_income", 0.0) for s in salary_slips)

    avg_bank_deposit = 0.0
    total_emi_debits = 0.0
    if bank_statements:
        avg_bank_deposit = sum(b.get("total_monthly_salary_credits", 0.0) for b in bank_statements) / len(bank_statements)
        total_emi_debits = sum(b.get("total_recurring_emi_debits", 0.0) for b in bank_statements) / len(bank_statements)

    income_variance = 0.0
    if gross_income > 0 and avg_bank_deposit > 0:
        income_variance = round(abs(gross_income - avg_bank_deposit) / gross_income * 100, 2)
        if income_variance > 20.0:
            critical_flags.append(
                f"Income variance > 20%: Payslip gross (₹{gross_income:,.2f}) vs Bank credits (₹{avg_bank_deposit:,.2f})"
            )

    # 3. Debt-to-Income (DTI) Calculation
    dti = 0.0
    if gross_income > 0:
        dti = round((total_emi_debits / gross_income) * 100, 2)

    if dti > 50.0:
        dti_risk = "HIGH"
        critical_flags.append(f"High DTI Ratio ({dti}%). Exceeds 50% prudent lending threshold.")
    elif dti > 35.0:
        dti_risk = "MODERATE"
    else:
        dti_risk = "LOW"

    # Determine final validation status
    if critical_flags:
        status = "FLAGGED" if len(critical_flags) <= 2 else "FAILED"
    else:
        status = "PASSED"

    return ValidationReport(
        name_check_passed=name_check_passed,
        name_discrepancies=name_discrepancies,
        income_variance_pct=income_variance,
        calculated_dti=dti,
        dti_risk_level=dti_risk,
        critical_flags=critical_flags,
        validation_status=status
    )