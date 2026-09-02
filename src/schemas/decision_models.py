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

    # Enriched Routing & Risk Intelligence
    routing_color: Literal["GREEN", "AMBER", "RED"] = "AMBER"
    routing_reason: str = ""
    requires_human_signoff: bool = True
    disposable_income: float = 0.0
    total_existing_emis: float = 0.0
    proposed_emi: float = 0.0

    # Statement Reconciliation & Eligibility
    statement_arithmetic_status: str = "NOT_AVAILABLE"
    statement_arithmetic_difference: float = 0.0
    eligibility_passed: bool = True
    eligibility_reasons: List[str] = Field(default_factory=list)

    # Factors & Audit
    factor_breakdown: Dict[str, Any] = Field(default_factory=dict)
    reviewer_checklist: List[str] = Field(default_factory=list)
    counterfactual_note: Optional[str] = None

    # Step Data Payloads
    step4_comparison: Optional[Dict[str, Any]] = None
    step5_calculation: Optional[Dict[str, Any]] = None
    step6_risk_anomaly: Optional[Dict[str, Any]] = None

    discrepancies: List[FieldComparison] = Field(default_factory=list)
    anomalies: List[Anomaly] = Field(default_factory=list)
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    audit_notes: str = ""