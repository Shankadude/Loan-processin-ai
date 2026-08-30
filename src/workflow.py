from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from src.utils.pdf_utils import document_to_base64_images
from src.agents.classifier import classify_document
from src.agents.extractor import extract_document_data
from src.agents.validator import validate_application_data, ValidationReport
from src.agents.underwriter import generate_underwriting_decision, UnderwritingDecision

# Most of this workflow is final, however if you think I(Shashank) am missing something feel free to tell me.

# --- Pipeline State Definition ---
class PipelineState(BaseModel):
    application_id: str
    declared_monthly_income: float
    requested_loan_amount: float
    raw_files: List[Dict[str, Any]] = Field(default_factory=list)  # [{"filename": str, "bytes": bytes}]

    # Ingestion & Extraction Outputs
    extracted_docs: List[Dict[str, Any]] = Field(default_factory=list)
    kyc_records: List[Dict[str, Any]] = Field(default_factory=list)
    salary_slips: List[Dict[str, Any]] = Field(default_factory=list)
    tax_forms: List[Dict[str, Any]] = Field(default_factory=list)
    bank_statements: List[Dict[str, Any]] = Field(default_factory=list)

    # Validation & Verdict
    validation_report: Optional[ValidationReport] = None
    underwriting_decision: Optional[UnderwritingDecision] = None


# --- Workflow Nodes ---
async def intake_and_extraction_node(state: PipelineState) -> dict:
    """Classifies and extracts structured data from each uploaded document."""
    extracted_docs = []
    kyc_records = []
    salary_slips = []
    tax_forms = []
    bank_statements = []

    for item in state.raw_files:
        filename = item["filename"]
        file_bytes = item["bytes"]

        # 1. Rasterize document to base64 images
        base64_images = document_to_base64_images(file_bytes, filename)

        # 2. Classify document
        classification = await classify_document(base64_images)
        doc_type = classification.document_type

        # 3. Dynamic schema extraction
        extracted_fields = await extract_document_data(doc_type, base64_images)

        doc_record = {
            "filename": filename,
            "document_type": doc_type,
            "confidence": classification.confidence,
            "issuer": classification.detected_issuer,
            "extracted_data": extracted_fields
        }
        extracted_docs.append(doc_record)

        # 4. Route extracted payload into category stores
        if doc_type in ["PAN_CARD", "IDENTITY_PROOF"]:
            kyc_records.append(extracted_fields)
        elif doc_type == "SALARY_SLIP":
            salary_slips.append(extracted_fields)
        elif doc_type == "FORM_16_OR_ITR":
            tax_forms.append(extracted_fields)
        elif doc_type == "BANK_STATEMENT":
            bank_statements.append(extracted_fields)

    return {
        "extracted_docs": extracted_docs,
        "kyc_records": kyc_records,
        "salary_slips": salary_slips,
        "tax_forms": tax_forms,
        "bank_statements": bank_statements
    }


async def validation_node(state: PipelineState) -> dict:
    """Performs deterministic cross-checks (DTI, name checks, income variance)."""
    report = validate_application_data(
        kyc_data=state.kyc_records,
        salary_slips=state.salary_slips,
        tax_forms=state.tax_forms,
        bank_statements=state.bank_statements
    )
    return {"validation_report": report}


async def underwriting_node(state: PipelineState) -> dict:
    """Synthesizes final approval, conditions, or adverse action notice."""
    applicant_summary = {
        "kyc": state.kyc_records,
        "salary_slips": state.salary_slips,
        "tax_forms": state.tax_forms,
        "bank_statements": state.bank_statements
    }

    decision = await generate_underwriting_decision(
        requested_amount=state.requested_loan_amount,
        declared_income=state.declared_monthly_income,
        validation_report=state.validation_report,
        applicant_summary=applicant_summary
    )
    return {"underwriting_decision": decision}


# --- Build & Compile Graph ---
def create_loan_pipeline_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("intake_and_extract", intake_and_extraction_node)
    graph.add_node("validate", validation_node)
    graph.add_node("underwrite", underwriting_node)

    graph.set_entry_point("intake_and_extract")
    graph.add_edge("intake_and_extract", "validate")
    graph.add_edge("validate", "underwrite")
    graph.add_edge("underwrite", END)

    return graph.compile()