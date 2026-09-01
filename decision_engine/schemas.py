from typing import Any, Dict, List

from pydantic import BaseModel, Field


class FinalDecision(BaseModel):
    """
    Final output of the complete loan decision pipeline.
    """

    applicant_id: str

    comparison: Dict[str, Any] = Field(
        default_factory=dict
    )

    calculations: Dict[str, Any] = Field(
        default_factory=dict
    )

    risk_assessment: Dict[str, Any] = Field(
        default_factory=dict
    )

    final_risk_score: int = 0

    final_risk_level: str = "LOW"

    recommendation: str = "REVIEW"

    audit_notes: str = ""