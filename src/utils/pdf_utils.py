import io
import base64
import pymupdf
from PIL import Image
from typing import List

def document_to_base64_images(file_bytes: bytes, filename: str, max_pages: int = 5) -> List[str]:
    """Converts a PDF or image byte stream into a list of base64 image strings."""
    images: List[Image.Image] = []
    lower_name = filename.lower()

    if lower_name.endswith(".pdf"):
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        for page_idx in range(min(len(doc), max_pages)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)
    elif lower_name.endswith((".png", ".jpg", ".jpeg")):
        images.append(Image.open(io.BytesIO(file_bytes)))
    else:
        raise ValueError(f"Unsupported file format: {filename}")

    base64_list = []
    for img in images:
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        base64_list.append(f"data:image/png;base64,{encoded}")

    return base64_list