import pymupdf
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import settings

print(f"✅ PyMuPDF version: {pymupdf.__version__}")

try:
    llm = ChatGoogleGenerativeAI(
        model=settings.VISION_MODEL,
        google_api_key=settings.GOOGLE_API_KEY
    )
    res = llm.invoke("Reply with 'Gemini API Connected Successfully' if you can read this.")
    
    # Handle both string responses and list-of-parts responses safely
    if isinstance(res.content, list):
        output_text = "".join([part.get("text", str(part)) if isinstance(part, dict) else str(part) for part in res.content])
    else:
        output_text = str(res.content)
        
    print(f"✅ LLM Status: {output_text.strip()}")
except Exception as e:
    print(f"❌ Gemini API Connection Failed: {e}")