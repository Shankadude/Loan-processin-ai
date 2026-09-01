import json
from typing import Literal, List
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from src.agents.llm_factory import get_reasoning_llm
from src.schemas.decision_models import DecisionResult


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
    validation_report: DecisionResult,
    applicant_summary: dict
) -> UnderwritingDecision:
    """Invokes Gemini to generate an explainable credit underwriting decision."""
    llm = get_reasoning_llm()
    structured_underwriter = llm.with_structured_output(UnderwritingDecision)

    # Safe extraction from DecisionResult
    dti_val = getattr(validation_report, "dti_percent", 0.0)
    risk_lvl = getattr(validation_report, "risk_level", "MEDIUM")
    inc_diff_pct = getattr(validation_report, "income_difference_percent", 0.0)
    overall_stat = getattr(validation_report, "overall_status", "UNKNOWN")
    risk_sc = getattr(validation_report, "risk_score", 0)
    
    anomalies_summary = [
        f"[{a.code}] {a.description} (Severity: {a.severity})"
        for a in getattr(validation_report, "anomalies", [])
    ]

    prompt = f"""
    You are a Senior Risk & Credit Underwriting Officer. Evaluate this loan application package:

    APPLICATION PARAMETERS:
    - Requested Loan Amount: ₹{requested_amount:,.2f}
    - Declared Monthly Income: ₹{declared_income:,.2f}

    DETERMINISTIC & POLICY METRICS:
    - Calculated DTI: {dti_val:.2f}%
    - Policy Risk Level: {risk_lvl}
    - Composite Risk Score: {risk_sc}/100
    - Income Discrepancy: {inc_diff_pct:.2f}%
    - Overall Verification Status: {overall_stat}
    - Detected Anomalies: {anomalies_summary}

    EXTRACTED APPLICANT DOCUMENTS:
    {json.dumps(applicant_summary, indent=2, default=str)}

    UNDERWRITING GUIDELINES:
    1. Maximum acceptable DTI is 50% for standard approval.
    2. Identity mismatch or severe income variance (>20%) requires MANUAL_REVIEW or REJECTED with Adverse Action notices.
    3. Low risk score (<30) and clean documents warrant standard approval.
    """

    decision: UnderwritingDecision = await structured_underwriter.ainvoke(
        [HumanMessage(content=prompt)]
    )
    return decision