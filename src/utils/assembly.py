from typing import List, Dict, Any
from src.schemas.document_models import ExtractedDocuments

REQUIRED_DOCUMENT_TYPES = ["PAYSLIP", "BANK_STATEMENT", "PAN_CARD"]

def find_missing_documents(documents: List[Dict[str, Any]]) -> List[str]:
    types_present = set()
    for doc in documents:
        t = doc.get("document_type") or doc.get("doc_type")
        if t:
            types_present.add(t)
            if t in ["SALARY_SLIP", "PAYSLIP"]:
                types_present.add("SALARY_SLIP")
                types_present.add("PAYSLIP")
            if t in ["FORM16", "FORM_16_OR_ITR"]:
                types_present.add("FORM16")
                types_present.add("FORM_16_OR_ITR")
            if t in ["PAN", "PAN_CARD"]:
                types_present.add("PAN")
                types_present.add("PAN_CARD")
            if t in ["AADHAAR", "AADHAAR_CARD", "IDENTITY_PROOF"]:
                types_present.add("AADHAAR")
                types_present.add("AADHAAR_CARD")
                types_present.add("IDENTITY_PROOF")
    return [req for req in REQUIRED_DOCUMENT_TYPES if req not in types_present]

def build_applicant_block(data: ExtractedDocuments) -> dict:
    full_name = None
    dob = None
    aadhaar_last4 = None

    if data.aadhaar_card:
        full_name = getattr(data.aadhaar_card, "full_name", None) or getattr(data.aadhaar_card, "name", None)
        dob = data.aadhaar_card.dob
        aadhaar_last4 = getattr(data.aadhaar_card, "aadhaar_last4", None)
    elif data.pan_card:
        full_name = getattr(data.pan_card, "full_name", None) or getattr(data.pan_card, "name", None)
        dob = data.pan_card.dob

    pan_number = data.pan_card.pan_number if data.pan_card else None

    return {
        "full_name": full_name,
        "pan_number": pan_number,
        "dob": dob,
        "aadhaar_last4": aadhaar_last4
    }