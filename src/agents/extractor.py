from typing import Dict, Any
from langchain_core.messages import HumanMessage
from src.agents.llm_factory import get_vision_llm
from src.schemas.kyc_schemas import PANCardExtract, IDProofExtract
from src.schemas.income_schemas import SalarySlipExtract, Form16ITRExtract
from src.schemas.bank_schemas import BankStatementExtract

# Schema routing table ----> need to be changed for the current database schema.
SCHEMA_REGISTRY = {
    "PAN_CARD": PANCardExtract,
    "IDENTITY_PROOF": IDProofExtract,
    "SALARY_SLIP": SalarySlipExtract,
    "FORM_16_OR_ITR": Form16ITRExtract,
    "BANK_STATEMENT": BankStatementExtract,
}

async def extract_document_data(doc_type: str, base64_images: list[str]) -> Dict[str, Any]:
    """Dynamically binds the relevant Pydantic schema and extracts structured fields."""
    target_schema = SCHEMA_REGISTRY.get(doc_type)

    # Fallback for unmapped or unknown documents
    if not target_schema:
        return {"document_type": doc_type, "note": "No specialized schema mapped for extraction."}

    llm = get_vision_llm()
    structured_extractor = llm.with_structured_output(target_schema)

    content_payload = [
        {
            "type": "text",
            "text": (
                f"Extract all relevant fields matching the {target_schema.__name__} schema. "
                "Ensure clean numeric values without commas or currency symbols."
            )
        }
    ]
    # Pass up to first 3 pages to the vision model for now.
    for img in base64_images[:3]:
        content_payload.append({"type": "image_url", "image_url": img})

    extracted_result = await structured_extractor.ainvoke([HumanMessage(content=content_payload)])
    return extracted_result.model_dump()