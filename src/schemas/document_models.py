from typing import Optional, List
from pydantic import BaseModel, Field

class PayslipLineItem(BaseModel):
    label: str
    amount: float

class PayslipData(BaseModel):
    employee_name: str
    employer_name: str
    pay_month: Optional[str] = None
    earnings: List[PayslipLineItem] = []
    deductions: List[PayslipLineItem] = []
    gross_earnings: float = 0.0
    total_deductions: float = 0.0
    net_pay: float = 0.0

class Transaction(BaseModel):
    date: str
    narration: str
    amount: float
    category: str  # e.g., salary_credit, emi_debit, upi_spend

class BankStatementData(BaseModel):
    account_holder_name: str
    bank_name: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_credits: float = 0.0
    total_debits: float = 0.0
    transactions: List[Transaction] = []

class Quarter(BaseModel):
    quarter: str
    tax_deducted: float

class Form16Data(BaseModel):
    employee_name: str
    pan_number: str
    employer_name: str
    assessment_year: str
    annual_gross: float = 0.0
    annual_tds: float = 0.0
    quarters: List[Quarter] = []

class PanCardData(BaseModel):
    name: str
    father_name: Optional[str] = None
    dob: str
    pan_number: str

class AadhaarCardData(BaseModel):
    name: str
    dob: str
    gender: Optional[str] = None
    address: Optional[str] = None
    aadhaar_last4: Optional[str] = None

class LoanApplicationData(BaseModel):
    name: str
    employer: str
    gross_monthly: float = 0.0
    net_monthly: float = 0.0
    loan_amount_requested: float = 0.0
    tenure_months: int = 12
    purpose: Optional[str] = None

class ExtractedDocuments(BaseModel):
    payslips: List[PayslipData] = []
    bank_statement: Optional[BankStatementData] = None
    form16: Optional[Form16Data] = None
    pan_card: Optional[PanCardData] = None
    aadhaar_card: Optional[AadhaarCardData] = None
    loan_application: Optional[LoanApplicationData] = None