from pydantic import BaseModel

from .income import IncomeMetrics
from .obligation import ObligationMetrics
from .statement import StatementValidationResult
from .eligibility import EligibilityResult


class RiskAssessmentResult(BaseModel):
    applicant_id: str

    income: IncomeMetrics
    obligations: ObligationMetrics
    statement: StatementValidationResult
    eligibility: EligibilityResult

    risk_score: float
    risk_level: str
    recommendation: str