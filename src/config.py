import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    MONGO_DETAILS: str = os.getenv("MONGO_DETAILS", "mongodb://localhost:27017/loan_db")
    VISION_MODEL: str = os.getenv("VISION_MODEL_NAME", "gemini-3.6-flash")
    REASONING_MODEL: str = os.getenv("REASONING_MODEL_NAME", "gemini-3.6-flash")

settings = Settings()
#added error msg to make sure u remember that key is loaded.
#IMPORTANT: Always use your own API key.
if not settings.GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing! Add it to your .env file.")