from pydantic import BaseModel, Field
from typing import Optional

# IMPORTANT: Update the schema as per our data.

class SalarySlipExtract(BaseModel):
    employee_name: str = Field(description="Name of the employee")
    employer_name: str = Field(description="Name of the employer or company")
    pay_period_end: Optional[str] = Field(default=None, description="End date of pay cycle")
    gross_income: float = Field(description="Gross salary amount before deductions")
    net_pay: float = Field(description="Net take-home salary amount")
    total_deductions: Optional[float] = Field(default=0.0, description="Total deductions")

class Form16ITRExtract(BaseModel):
    taxpayer_name: str = Field(description="Name of the taxpayer")
    assessment_year: str = Field(description="Assessment year e.g. 2024-25")
    gross_total_income: float = Field(description="Total gross taxable income")
    total_tax_paid: float = Field(description="Total tax deducted/paid")