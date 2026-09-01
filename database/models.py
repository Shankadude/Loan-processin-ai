from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class Applicant(BaseModel):
    role: str = "primary"
    full_name: Optional[str] = None
    pan_number: Optional[str] = None
    aadhaar_last4: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    employer_name: Optional[str] = None
    designation: Optional[str] = None
    employment_type: str = "salaried"


class DocumentMetadata(BaseModel):
    original_filename: str
    doc_type: str
    doc_month: Optional[str] = None
    trust_tier: int = 1
    trust_tier_reason: Optional[str] = None
    processing_status: str = "done"
    extracted: Optional[dict[str, Any]] = None


class CrossCheck(BaseModel):
    check_type: str
    declared_value: Optional[str] = None
    verified_value: Optional[str] = None
    match_result: str
    discrepancy_amount: Optional[float] = None
    severity: str = "minor"
    explanation: Optional[str] = None


class EntityRelationship(BaseModel):
    source: dict[str, str]
    relationship: str
    target: dict[str, str]
    properties: dict[str, Any] = Field(default_factory=dict)


class Application(BaseModel):
    application_ref: str
    loan_type: str = "personal_loan"
    status: str = "pending"
    routing: dict[str, Any] = Field(default_factory=lambda: {"color": None, "reason": None})
    risk: dict[str, Any] = Field(default_factory=dict)
    financials: dict[str, Any] = Field(default_factory=dict)
    applicants: list[Applicant] = Field(default_factory=list)
    documents: list[DocumentMetadata] = Field(default_factory=list)
    cross_checks: list[CrossCheck] = Field(default_factory=list)
    entity_graph: list[EntityRelationship] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractedField(BaseModel):
    application_ref: str
    doc_type: str
    field_name: str
    field_value: str
    numeric_value: Optional[float] = None
    source_type: str = "verified"
    evidence: dict[str, Any] = Field(default_factory=lambda: {
        "page_number": 1,
        "bounding_box": None,
        "quoted_text": None,
        "quote_verified": True,
        "confidence": 0.95
    })
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BankTransaction(BaseModel):
    application_ref: str
    txn_date: Optional[str] = None
    description: str
    amount: float
    txn_type: str
    category: str = "other"
    is_salary_match: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(BaseModel):
    application_ref: str
    actor: str
    action: str
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyEmbedding(BaseModel):
    policy_name: str
    loan_type: str = "personal_loan"
    chunk_index: int
    chunk_text: str
    embedding: Optional[list[float]] = None
    section_title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
