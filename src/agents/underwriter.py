import json
from typing import Literal, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from src.agents.llm_factory import get_reasoning_llm
from src.agents.validator import ValidationReport

# Still not sure about how do we certifiy the approval. This one is suggested by AI. works for now.
# Its deterministic and much safe.
class UnderwritingDecision(BaseModel):
    verdict: Literal["APPROVED", "CONDITIONALLY_APPROVED", "REJECTED", "MANUAL_REVIEW"] = Field(
        description="Final credit underwriting recommendation"
    )
    risk_score_summary: str = Field(description="Summary of the credit and debt profile")
    conditions: List[str] = Field(
        default_factory=list,
        description="Conditions required prior to disbursement (if conditionally approved)"
    )
    adverse_action_reasons: List[str] = Field(
        default_factory=list,
        description="Regulatory ECOA/FCRA compliant reasons if application is rejected"
    )
    executive_rationale: str = Field(description="2-3 sentence overview for the human loan officer")

async def generate_underwriting_decision(
    requested_amount: float,
    declared_income: float,
    validation_report: ValidationReport,
    applicant_summary: dict
) -> UnderwritingDecision:
    """Invokes Gemini to generate an explainable credit underwriting decision."""
    llm = get_reasoning_llm()
    structured_underwriter = llm.with_structured_output(UnderwritingDecision)

    prompt = f"""
    You are a Senior Risk & Credit Underwriting Officer. Evaluate this loan application package:

    APPLICATION PARAMETERS:
    - Requested Loan Amount: ₹{requested_amount:,.2f}
    - Declared Monthly Income: ₹{declared_income:,.2f}

    DETERMINISTIC VALIDATION METRICS:
    - Calculated DTI: {validation_report.calculated_dti}% (Risk Level: {validation_report.dti_risk_level})
    - Income Discrepancy: {validation_report.income_variance_pct}%
    - Name Check Passed: {validation_report.name_check_passed}
    - Critical Red Flags: {validation_report.critical_flags}
    - Validation Status: {validation_report.validation_status}

    EXTRACTED APPLICANT DETAILS:
    {json.dumps(applicant_summary, indent=2)}

    UNDERWRITING GUIDELINES:
    1. Maximum acceptable DTI is 45% for approval.
    2. Name mismatch or severe income variance (>20%) requires MANUAL_REVIEW or CONDITIONALLY_APPROVED with additional proof.
    3. If DTI > 50% or validation status is FAILED, mark as REJECTED and provide clear Adverse Action reason codes.
    """

    decision: UnderwritingDecision = await structured_underwriter.ainvoke(
        [HumanMessage(content=prompt)]
    )
    return decision