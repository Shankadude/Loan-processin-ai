import re
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

from src.utils.pdf_utils import document_to_base64_images, extract_pdf_text_and_images
from src.agents.extractor import process_document_unified, parse_digital_document_text
from src.agents.underwriter import generate_underwriting_decision, UnderwritingDecision
from src.schemas.decision_models import DecisionResult
from src.decision_engine.comparison import compare_identity, compare_income, compare_employer, compare_pan
from src.decision_engine.extractors import extract_declared, extract_verified, extract_liabilities
from src.decision_engine.risk_scorer import score_application


class PipelineState(BaseModel):
    application_id: str
    declared_monthly_income: float
    requested_loan_amount: float
    raw_files: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_docs: List[Dict[str, Any]] = Field(default_factory=list)
    decision_result: Optional[DecisionResult] = None
    underwriting_decision: Optional[UnderwritingDecision] = None


async def intake_and_extraction_node(state: PipelineState) -> dict:
    applicant_context: Dict[str, Any] = {}

    # 1. Pre-scan native digital PDFs to establish applicant context for decryption & fallback
    for item in state.raw_files:
        fn = item["filename"].lower()
        if ("loan" in fn or "application" in fn) and fn.endswith(".pdf"):
            try:
                raw_text, _ = extract_pdf_text_and_images(item["bytes"], item["filename"])
                if raw_text:
                    parsed = parse_digital_document_text(raw_text, item["filename"])
                    if parsed and parsed.get("extracted_data"):
                        d = parsed["extracted_data"]
                        for key in ["name", "dob", "pan", "employer", "gross_monthly", "net_monthly", "loan_amount_requested", "declared_total_emi"]:
                            if d.get(key):
                                applicant_context[key] = d[key]
                        break
            except Exception:
                pass

    if not applicant_context.get("name"):
        for item in state.raw_files:
            fn = item["filename"].lower()
            if ("form16" in fn or "payslip" in fn or "salary" in fn) and fn.endswith(".pdf"):
                try:
                    raw_text, _ = extract_pdf_text_and_images(item["bytes"], item["filename"])
                    if raw_text:
                        parsed = parse_digital_document_text(raw_text, item["filename"])
                        if parsed and parsed.get("extracted_data"):
                            d = parsed["extracted_data"]
                            if d.get("employee_name"): applicant_context["name"] = d.get("employee_name")
                            if d.get("pan_number"): applicant_context["pan"] = d.get("pan_number")
                            if d.get("employer_name"): applicant_context["employer"] = d.get("employer_name")
                            if applicant_context.get("name"): break
                except Exception:
                    pass

    # 2. Hybrid Extraction Loop (Digital Fast-Path + Vision Fallback)
    extracted_docs = []
    for item in state.raw_files:
        filename = item["filename"]
        file_bytes = item["bytes"]

        try:
            if filename.lower().endswith(".pdf"):
                raw_text, base64_images = extract_pdf_text_and_images(
                    file_bytes, filename, applicant_context=applicant_context
                )
            else:
                raw_text = ""
                base64_images = document_to_base64_images(file_bytes, filename)

            # Passes digital text and applicant context to bypass vision LLM if text is extractable
            doc_res = await process_document_unified(
                base64_images=base64_images,
                raw_text=raw_text,
                filename=filename,
                applicant_context=applicant_context
            )
            doc_type = doc_res["document_type"]
            if doc_type in ["SALARY_SLIP", "PAYSLIP"]:
                doc_type = "PAYSLIP"
            elif doc_type in ["FORM16", "FORM_16_OR_ITR"]:
                doc_type = "FORM_16_OR_ITR"
            elif doc_type in ["PAN", "PAN_CARD"]:
                doc_type = "PAN_CARD"

            extracted_fields = doc_res["extracted_data"]

            extracted_docs.append({
                "filename": filename,
                "doc_type": doc_type,
                "document_type": doc_type,
                "confidence": doc_res["confidence"],
                "extracted": extracted_fields,
                "extracted_data": extracted_fields
            })
        except Exception as doc_err:
            print(f"Warning: Failed to extract {filename}: {doc_err}")
            extracted_docs.append({
                "filename": filename,
                "doc_type": "UNKNOWN",
                "document_type": "UNKNOWN",
                "confidence": 0.0,
                "extracted": {"error": str(doc_err)},
                "extracted_data": {"error": str(doc_err)}
            })

    return {"extracted_docs": extracted_docs}


async def validation_node(state: PipelineState) -> dict:
    payload = {
        "_id": state.application_id,
        "documents": state.extracted_docs,
        "financials": {
            "loan_request": {
                "declared_net_monthly": state.declared_monthly_income,
                "requested_amount": state.requested_loan_amount
            }
        }
    }

    declared = extract_declared(payload)
    
    # Auto-fallback to extracted loan application figures if manual UI inputs were left as 0
    loan_doc = next(
        (d for d in state.extracted_docs if (d.get("doc_type") or d.get("document_type")) == "LOAN_APPLICATION"),
        None
    )
    loan_ext = (loan_doc.get("extracted_data") or loan_doc.get("extracted") or {}) if loan_doc else {}

    # If document has declared income, prioritize it over default UI forms
    doc_net = float(loan_ext.get("net_monthly") or loan_ext.get("gross_monthly") or 0.0)
    if doc_net > 0 and (state.declared_monthly_income == 0.0 or not declared.get("net_monthly")):
        declared["net_monthly"] = doc_net

    doc_req_amt = float(loan_ext.get("loan_amount_requested") or 0.0)
    effective_req_amt = state.requested_loan_amount if state.requested_loan_amount > 0 else doc_req_amt

    verified = extract_verified(payload)
    liabilities = extract_liabilities(payload)

    # 1. Deterministic Cross-Document Comparisons
    comparisons = compare_identity(declared, verified, all_docs=state.extracted_docs)
    comparisons.append(compare_pan(declared, verified))
    comparisons.append(compare_income(declared, verified))
    comparisons.append(compare_employer(declared, verified))

    # 2. Extract Bank Statement for Balance Reconciliation
    bank_doc = next(
        (d for d in state.extracted_docs if (d.get("doc_type") or d.get("document_type")) == "BANK_STATEMENT"),
        None
    )
    bank_data = (bank_doc.get("extracted_data") or bank_doc.get("extracted") or {}) if bank_doc else {}

    # 3. Comprehensive Risk Scoring with Proposed Loan Obligations
    decision_res = score_application(
        application_id=state.application_id,
        declared_payload=declared,
        verified_payload=verified,
        liabilities_payload=liabilities,
        comparisons=comparisons,
        bank_statement_data=bank_data,
        requested_amount=effective_req_amt,
    )
    return {"decision_result": decision_res}


async def underwriting_node(state: PipelineState) -> dict:
    decision = await generate_underwriting_decision(
        requested_amount=state.requested_loan_amount,
        declared_income=state.declared_monthly_income,
        validation_report=state.decision_result,
        applicant_summary={"documents": state.extracted_docs}
    )
    return {"underwriting_decision": decision}


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