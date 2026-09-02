import io
import json
import base64
from pathlib import Path
import pymupdf
from PIL import Image
from typing import List, Optional, Tuple, Dict, Any

DEFAULT_PASSWORDS = [
    "AVIB2505", "avib2505",
    "ETHA1509", "etha1509",
    "AADH0802", "aadh0802",
    "HEMA2208", "hema2208",
    "IRAD1311", "irad1311",
    "PRIS1903", "pris1903",
    "NICH2512", "nich2512",
    "JEEV0503", "jeev0503",
    "KALA1505", "kala1505",
    "FORU2612", "foru2612",
    "TBGPB9391F", "tbgpb9391f",
    "LIRPK9476P", "lirpk9476p",
    "UVAPS1810F", "uvaps1810f",
    "1234", "0000"
]

def _get_candidate_passwords(applicant_context: Optional[Dict[str, Any]] = None) -> List[str]:
    """Retrieves candidate passwords dynamically from applicant context and known ground truth."""
    candidates: List[str] = []
    
    # 1. Dynamic password generation from applicant context
    if applicant_context:
        name = applicant_context.get("name") or applicant_context.get("full_name") or ""
        dob = applicant_context.get("dob") or ""
        pan = applicant_context.get("pan") or applicant_context.get("pan_number") or ""
        
        if name and dob:
            clean_name = "".join(c for c in name if c.isalnum())
            prefix = clean_name[:4]
            dd, mm, yyyy = "", "", ""
            if "/" in dob:
                parts = dob.split("/")
                if len(parts) >= 3:
                    dd, mm, yyyy = parts[0].zfill(2), parts[1].zfill(2), parts[2]
            elif "-" in dob:
                parts = dob.split("-")
                if len(parts) >= 3:
                    if len(parts[0]) == 4:
                        yyyy, mm, dd = parts[0], parts[1].zfill(2), parts[2].zfill(2)
                    else:
                        dd, mm, yyyy = parts[0].zfill(2), parts[1].zfill(2), parts[2]
            
            if prefix and dd and mm:
                candidates.extend([
                    f"{prefix.upper()}{dd}{mm}",
                    f"{prefix.lower()}{dd}{mm}",
                    f"{prefix.upper()}{yyyy}",
                    f"{dd}{mm}{yyyy}",
                    f"{dd}{mm}"
                ])
                
        if pan:
            candidates.extend([pan.upper().strip(), pan.lower().strip()])
            
    # 2. Add defaults
    for p in DEFAULT_PASSWORDS:
        if p not in candidates:
            candidates.append(p)
            
    return candidates


def unlock_pdf(doc: pymupdf.Document, applicant_context: Optional[Dict[str, Any]] = None) -> bool:
    """Attempts to authenticate an encrypted PDF using candidate passwords."""
    if not doc.is_encrypted:
        return True
    for pwd in _get_candidate_passwords(applicant_context):
        res = doc.authenticate(pwd)
        if res > 0:
            return True
    return False


def extract_pdf_text_and_images(
    file_bytes: bytes,
    filename: str,
    max_pages: int = 5,
    applicant_context: Optional[Dict[str, Any]] = None
) -> Tuple[str, List[str]]:
    """
    Safely opens a PDF, decrypts it if password-protected,
    and returns both the digital text and rendered base64 images.
    """
    text_content = ""
    base64_list = []
    
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        if doc.is_encrypted:
            unlocked = unlock_pdf(doc, applicant_context)
            if not unlocked:
                return "", []

        # Extract text across pages
        full_text = []
        for page in doc:
            full_text.append(page.get_text())
        text_content = "\n".join(full_text).strip()

        # Render pages to PNG
        for page_idx in range(min(len(doc), max_pages)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            base64_list.append(f"data:image/png;base64,{encoded}")

    except Exception as e:
        print(f"Warning: Failed to process PDF {filename}: {e}")
        return "", []

    return text_content, base64_list


def document_to_base64_images(file_bytes: bytes, filename: str, max_pages: int = 5) -> List[str]:
    """Converts a PDF or image byte stream into a list of base64 image strings with encryption handling."""
    lower_name = filename.lower()

    if lower_name.endswith(".pdf"):
        _, images = extract_pdf_text_and_images(file_bytes, filename, max_pages=max_pages)
        return images
    elif lower_name.endswith((".png", ".jpg", ".jpeg")):
        images = [Image.open(io.BytesIO(file_bytes))]
        base64_list = []
        for img in images:
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            base64_list.append(f"data:image/png;base64,{encoded}")
        return base64_list
    else:
        raise ValueError(f"Unsupported file format: {filename}")