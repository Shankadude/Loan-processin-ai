from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

Status = Literal["MATCH", "PARTIAL_MATCH", "MISMATCH", "NOT_AVAILABLE"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
RiskRecommendation = Literal["AUTO_APPROVE", "REVIEW", "REJECT", "CONDITIONALLY_APPROVED"]

class Evidence(BaseModel):
    source_document: str
    source_path: str
    field: str
    value: Any
    evidence_type: Literal["DECLARED", "VERIFIED", "TRANSACTION", "DERIVED"]
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
    comparison_method: Literal["DETERMINISTIC", "LLM_SEMANTIC", "NOT_AVAILABLE"] = "DETERMINISTIC"
    evidence: List[Evidence] = Field(default_factory=list)
    reason: str = ""

class Anomaly(BaseModel):
    code: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    description: str
    source: str
    evidence: Dict[str, Any] = Field(default_factory=dict)

class RiskFactor(BaseModel):
    factor: str
    score: int
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    reason: str
    source: str

class DecisionResult(BaseModel):
    application_id: str
    overall_status: Status
    identity_status: Status
    income_status: Status
    liability_status: Status
    declared_monthly_net: float
    verified_monthly_net: float
    income_difference_percent: float
    declared_emi: float
    detected_emi: float
    dti_percent: float
    risk_score: int
    risk_level: RiskLevel
    recommendation: RiskRecommendation
    discrepancies: List[FieldComparison] = Field(default_factory=list)
    anomalies: List[Anomaly] = Field(default_factory=list)
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    audit_notes: str = ""