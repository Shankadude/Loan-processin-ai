from typing import List, Dict, Any
from src.schemas.document_models import ExtractedDocuments

REQUIRED_DOCUMENT_TYPES = ["PAYSLIP", "BANK_STATEMENT", "PAN_CARD"]

def find_missing_documents(documents: List[Dict[str, Any]]) -> List[str]:
    """Identifies missing mandatory documents from the ingested set."""
    types_present = {doc.get("document_type") or doc.get("doc_type") for doc in documents}
    return [req for req in REQUIRED_DOCUMENT_TYPES if req not in types_present]

def build_applicant_block(data: ExtractedDocuments) -> dict:
    """Builds the canonical applicant identity block from PAN and Aadhaar records."""
    full_name = None
    dob = None
    aadhaar_last4 = None

    if data.aadhaar_card:
        full_name = data.aadhaar_card.name
        dob = data.aadhaar_card.dob
        aadhaar_last4 = data.aadhaar_card.aadhaar_last4
    elif data.pan_card:
        full_name = data.pan_card.name
        dob = data.pan_card.dob

    pan_number = data.pan_card.pan_number if data.pan_card else None

    return {
        "full_name": full_name,
        "pan_number": pan_number,
        "dob": dob,
        "aadhaar_last4": aadhaar_last4
    }