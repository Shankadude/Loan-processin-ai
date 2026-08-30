import asyncio
from src.utils.pdf_utils import document_to_base64_images
from src.agents.classifier import classify_document
from src.agents.extractor import extract_document_data
from PIL import Image, ImageDraw
import io

def create_dummy_pan_image() -> bytes:
    """Generates an in-memory sample PAN card image for testing."""
    img = Image.new("RGB", (600, 350), color="#e8f4f8")
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "INCOME TAX DEPARTMENT - GOVT OF INDIA", fill="black")
    draw.text((30, 80), "Permanent Account Number Card", fill="black")
    draw.text((30, 140), "Name: SHASHANK DATTU", fill="black")
    draw.text((30, 180), "Father's Name: DATTU", fill="black")
    draw.text((30, 220), "DOB: 15/08/1998", fill="black")
    draw.text((30, 270), "PAN: ABCDE1234F", fill="blue")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

async def run_test():
    print("🚀 Generating test document image...")
    dummy_bytes = create_dummy_pan_image()
    
    print("🖼️ Converting to base64 payload...")
    base64_imgs = document_to_base64_images(dummy_bytes, "test_pan.png")

    print("🤖 Running Classifier Agent...")
    classification = await classify_document(base64_imgs)
    print(f"✅ Classified Type: {classification.document_type} (Confidence: {classification.confidence:.2f})")

    print("🔍 Running Dynamic Schema Extractor...")
    extracted_data = await extract_document_data(classification.document_type, base64_imgs)
    print("✅ Extracted Data:")
    for key, value in extracted_data.items():
        print(f"   • {key}: {value}")

if __name__ == "__main__":
    asyncio.run(run_test())