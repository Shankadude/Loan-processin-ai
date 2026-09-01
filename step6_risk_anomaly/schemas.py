from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


RiskLevel = Literal[
    "LOW",
    "MEDIUM",
    "HIGH"
]

RiskRecommendation = Literal[
    "AUTO_APPROVE",
    "REVIEW",
    "REJECT"
]


class RiskFactor(BaseModel):
    """
    Represents one factor contributing to the risk score.
    """

    factor: str

    score: int

    severity: Literal[
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    reason: str

    source: str


class Anomaly(BaseModel):
    """
    Represents an anomaly detected during
    comparison/risk assessment.
    """

    code: str

    severity: Literal[
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    description: str

    source: str

    evidence: Dict[str, Any] = Field(
        default_factory=dict
    )


class RiskAssessment(BaseModel):
    """
    Final output of Step 6.
    """

    applicant_id: str

    risk_score: int

    risk_level: RiskLevel

    recommendation: RiskRecommendation

    risk_factors: List[RiskFactor] = Field(
        default_factory=list
    )

    anomalies: List[Anomaly] = Field(
        default_factory=list
    )

    audit_notes: str = ""