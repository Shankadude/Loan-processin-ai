from pydantic import BaseModel, Field
from typing import Optional, List

# IMPORTANT: Update the schema as per our data.

class BankTransaction(BaseModel):
    date: str = Field(description="Transaction date")
    description: str = Field(description="Narration or description")
    amount: float = Field(description="Transaction amount in INR")
    tx_type: str = Field(description="'CREDIT' or 'DEBIT'")

class BankStatementExtract(BaseModel):
    account_holder_name: str = Field(description="Primary account holder's name")
    bank_name: str = Field(description="Name of the bank")
    account_number_last4: Optional[str] = Field(default=None, description="Last 4 digits of account number")
    statement_period: Optional[str] = Field(default=None, description="Statement duration / month range")
    total_monthly_salary_credits: float = Field(default=0.0, description="Sum of recurring payroll/salary credits")
    total_recurring_emi_debits: float = Field(default=0.0, description="Sum of recurring loan/EMI debits")
    average_monthly_balance: Optional[float] = Field(default=0.0, description="Average running balance")