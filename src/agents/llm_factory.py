from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import settings
# most of the stuff is pre-determined so try not to change anything here.
def get_vision_llm():
    return ChatGoogleGenerativeAI(
        model=settings.VISION_MODEL,
        max_retries=5,
        google_api_key=settings.GOOGLE_API_KEY
    )

def get_reasoning_llm():
    return ChatGoogleGenerativeAI(
        model=settings.REASONING_MODEL,
        max_retries=5,
        google_api_key=settings.GOOGLE_API_KEY
    )