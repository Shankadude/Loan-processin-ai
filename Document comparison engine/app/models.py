from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


Status = Literal[
    "MATCH",
    "PARTIAL_MATCH",
    "MISMATCH",
    "NOT_AVAILABLE"
]


class Evidence(BaseModel):
    source_document: str
    source_path: str
    field: str
    value: Any
    evidence_type: Literal[
        "DECLARED",
        "VERIFIED",
        "TRANSACTION",
        "DERIVED"
    ]
    note: Optional[str] = None


class FieldComparison(BaseModel):
    field: str

    declared_value: Any = None
    verified_value: Any = None

    normalized_declared: Any = None
    normalized_verified: Any = None

    status: Status

    discrepancy_amount: Optional[float] = None
    discrepancy_percent: Optional[float] = None

    comparison_method: Literal[
        "DETERMINISTIC",
        "LLM_SEMANTIC",
        "NOT_AVAILABLE"
    ]

    evidence: List[Evidence] = Field(default_factory=list)

    reason: str = ""


class SemanticFinding(BaseModel):
    field: str
    status: Status
    reason: str
    confidence: float = 0.0


class ComparisonResult(BaseModel):

    applicant_id: str

    identity_status: Status
    income_status: Status
    liability_status: Status

    overall_status: Status

    declared_monthly_net: float
    verified_monthly_net: float

    income_difference: float
    income_difference_percent: float

    declared_emi: float
    detected_emi: float

    dti_percent: float

    discrepancies: List[FieldComparison]

    semantic_findings: List[SemanticFinding]

    anomalies: List[str]

    evidence: List[Evidence]

    risk_level: Literal[
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    recommendation: Literal[
        "AUTO_APPROVE",
        "REVIEW",
        "REJECT"
    ]

    audit_notes: str