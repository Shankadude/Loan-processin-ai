from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from src.agents.llm_factory import get_vision_llm

class ClassificationOutput(BaseModel):
    document_type: Literal[
        "PAN_CARD",
        "IDENTITY_PROOF",      # Aadhaar, Passport, Voter ID, Driving License
        "SALARY_SLIP",
        "FORM_16_OR_ITR",
        "BANK_STATEMENT",
        "UNKNOWN"
    ] = Field(description="The primary classification category for this document")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    detected_issuer: str = Field(description="Name of bank, company, or government authority detected")

async def classify_document(base64_images: list[str]) -> ClassificationOutput:
    """Classifies the document category based on the first page visual layout."""
    llm = get_vision_llm()
    structured_classifier = llm.with_structured_output(ClassificationOutput)

    content_payload = [
        {
            "type": "text",
            "text": (
                "You are an expert Indian financial document classifier. "
                "Analyze this image and identify the document category, confidence score, and issuer."
            )
        },
        {"type": "image_url", "image_url": base64_images[0]}  # Classify using first page can be changed as per need
    ]

    result: ClassificationOutput = await structured_classifier.ainvoke(
        [HumanMessage(content=content_payload)]
    )
    return result