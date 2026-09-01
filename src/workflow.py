import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from src.utils.pdf_utils import document_to_base64_images
from src.agents.extractor import process_document_unified
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
    extracted_docs = []
    for item in state.raw_files:
        filename = item["filename"]
        file_bytes = item["bytes"]
        base64_images = document_to_base64_images(file_bytes, filename)

        # Single combined classification + extraction call
        doc_res = await process_document_unified(base64_images)
        doc_type = doc_res["document_type"]
        extracted_fields = doc_res["extracted_data"]

        extracted_docs.append({
            "filename": filename,
            "doc_type": doc_type,
            "document_type": doc_type,
            "confidence": doc_res["confidence"],
            "extracted": extracted_fields,
            "extracted_data": extracted_fields
        })

        # Throttle between calls to prevent bursting limits
        await asyncio.sleep(1)

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
    if not declared.get("net_monthly") and state.declared_monthly_income > 0:
        declared["net_monthly"] = state.declared_monthly_income

    verified = extract_verified(payload)
    liabilities = extract_liabilities(payload)

    # Cross-document name verification against all uploaded files
    comparisons = compare_identity(declared, verified, all_docs=state.extracted_docs)
    comparisons.append(compare_pan(payload, verified))
    comparisons.append(compare_income(declared, verified))
    comparisons.append(compare_employer(declared, verified))

    decision_res = score_application(
        application_id=state.application_id,
        declared_payload=declared,
        verified_payload=verified,
        liabilities_payload=liabilities,
        comparisons=comparisons
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