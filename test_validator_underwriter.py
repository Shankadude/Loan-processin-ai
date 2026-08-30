import asyncio
from src.agents.validator import validate_application_data
from src.agents.underwriter import generate_underwriting_decision

async def run_pipeline_test():
    print("📋 Generating synthetic multi-document payload...")

    # Mock extracted document inputs
    mock_kyc = [{
        "full_name": "Shashank Dattu",
        "pan_number": "ABCDE1234F",
        "dob": "15/08/1998"
    }]
    mock_payslips = [{
        "employee_name": "Shashank Dattu",
        "employer_name": "Tech Corp Pvt Ltd",
        "gross_income": 95000.0,
        "net_pay": 76000.0
    }]
    mock_bank_stmts = [{
        "account_holder_name": "Shashank Dattu",
        "bank_name": "HDFC Bank",
        "total_monthly_salary_credits": 94000.0,
        "total_recurring_emi_debits": 28000.0,
        "average_monthly_balance": 45000.0
    }]

    print("⚙️ Running Deterministic Validator Node...")
    validation_report = validate_application_data(
        kyc_data=mock_kyc,
        salary_slips=mock_payslips,
        tax_forms=[],
        bank_statements=mock_bank_stmts
    )

    print(f"✅ Name Match: {validation_report.name_check_passed}")
    print(f"✅ Calculated DTI: {validation_report.calculated_dti}% ({validation_report.dti_risk_level})")
    print(f"✅ Validation Status: {validation_report.validation_status}")

    print("\n🤖 Running Underwriting Decision Agent (Gemini)...")
    decision = await generate_underwriting_decision(
        requested_amount=500000.0,
        declared_income=95000.0,
        validation_report=validation_report,
        applicant_summary={
            "kyc": mock_kyc,
            "income": mock_payslips,
            "bank": mock_bank_stmts
        }
    )

    print(f"\n🏁 Decision Verdict: {decision.verdict}")
    print(f"📝 Executive Rationale: {decision.executive_rationale}")
    if decision.conditions:
        print(f"⚠️ Conditions: {decision.conditions}")
    if decision.adverse_action_reasons:
        print(f"❌ Adverse Action: {decision.adverse_action_reasons}")

if __name__ == "__main__":
    asyncio.run(run_pipeline_test())