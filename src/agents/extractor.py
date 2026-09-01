import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from src.agents.llm_factory import get_vision_llm
from src.schemas.document_models import (
    PanCardData,
    AadhaarCardData,
    PayslipData,
    Form16Data,
    BankStatementData,
    LoanApplicationData,
)


class UnifiedDocumentExtraction(BaseModel):
    document_type: str = Field(
        description="One of: PAN_CARD, IDENTITY_PROOF, SALARY_SLIP, FORM_16_OR_ITR, BANK_STATEMENT, LOAN_APPLICATION, UNKNOWN"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    pan_card: Optional[PanCardData] = None
    aadhaar_card: Optional[AadhaarCardData] = None
    salary_slip: Optional[PayslipData] = None
    form16: Optional[Form16Data] = None
    bank_statement: Optional[BankStatementData] = None
    loan_application: Optional[LoanApplicationData] = None


async def process_document_unified(base64_images: list[str]) -> Dict[str, Any]:
    """Classifies and extracts document fields in a single multimodal LLM call."""
    llm = get_vision_llm()
    structured_extractor = llm.with_structured_output(UnifiedDocumentExtraction)

    prompt = (
        "Analyze this Indian financial/identity document. Identify its document type and extract all fields cleanly "
        "matching the appropriate sub-schema. Ensure all numbers are clean floats without commas or currency symbols."
    )

    content_payload = [{"type": "text", "text": prompt}]
    for img in base64_images[:2]:
        content_payload.append({"type": "image_url", "image_url": img})

    result: UnifiedDocumentExtraction = await structured_extractor.ainvoke(
        [HumanMessage(content=content_payload)]
    )

    doc_type = result.document_type
    extracted_data = {}

    if doc_type == "PAN_CARD" and result.pan_card:
        extracted_data = result.pan_card.model_dump()
    elif doc_type == "IDENTITY_PROOF" and result.aadhaar_card:
        extracted_data = result.aadhaar_card.model_dump()
    elif (doc_type in ["SALARY_SLIP", "PAYSLIP"]) and result.salary_slip:
        extracted_data = result.salary_slip.model_dump()
    elif (doc_type in ["FORM_16_OR_ITR", "FORM16"]) and result.form16:
        extracted_data = result.form16.model_dump()
    elif doc_type == "BANK_STATEMENT" and result.bank_statement:
        extracted_data = result.bank_statement.model_dump()
    elif doc_type == "LOAN_APPLICATION" and result.loan_application:
        extracted_data = result.loan_application.model_dump()

    return {
        "document_type": doc_type,
        "confidence": result.confidence,
        "extracted_data": extracted_data,
    }