from typing import Optional, List
from pydantic import BaseModel, Field


class PayslipLineItem(BaseModel):
    label: str
    amount: float


class PayslipData(BaseModel):
    employee_name: str
    employer_name: str
    pay_month: Optional[str] = None
    gross_earnings: float = 0.0
    total_deductions: float = 0.0
    net_pay: float = 0.0
    pan_number: Optional[str] = None
    earnings: List[PayslipLineItem] = Field(default_factory=list)
    deductions: List[PayslipLineItem] = Field(default_factory=list)


class Transaction(BaseModel):
    date: str
    narration: str
    amount: float
    category: str = "other"  # salary_credit, emi_debit, upi_spend


class BankStatementData(BaseModel):
    account_holder_name: str
    bank_name: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_credits: float = 0.0
    total_debits: float = 0.0
    total_monthly_salary_credits: float = 0.0
    total_recurring_emi_debits: float = 0.0
    transactions: List[Transaction] = Field(default_factory=list)


class Form16Data(BaseModel):
    employee_name: str
    pan_number: str
    employer_name: str
    assessment_year: Optional[str] = None
    annual_gross: float = 0.0
    annual_tds: float = 0.0


class PanCardData(BaseModel):
    full_name: str
    pan_number: str
    dob: str
    father_name: Optional[str] = None


class AadhaarCardData(BaseModel):
    full_name: str
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    id_type: Optional[str] = "AADHAAR"


class LoanApplicationData(BaseModel):
    name: str
    dob: Optional[str] = None
    pan_number: Optional[str] = None
    employer: str
    gross_monthly: float = 0.0
    net_monthly: float = 0.0
    loan_amount_requested: float = 0.0
    tenure_months: int = 12
    purpose: Optional[str] = None
    address: Optional[str] = None
    liabilities: List[dict] = Field(default_factory=list)


class ExtractedDocuments(BaseModel):
    payslips: List[PayslipData] = Field(default_factory=list)
    bank_statement: Optional[BankStatementData] = None
    form16: Optional[Form16Data] = None
    pan_card: Optional[PanCardData] = None
    aadhaar_card: Optional[AadhaarCardData] = None
    loan_application: Optional[LoanApplicationData] = None