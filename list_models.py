import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ Error: GOOGLE_API_KEY is not set in .env")
    exit()

genai.configure(api_key=api_key)

print("🔍 Querying available models for your API key...")
try:
    available_models = []
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            name = model.name.replace("models/", "")
            available_models.append(name)
            print(f"  • {name}")
            
    if available_models:
        print(f"\n✅ Success! Use '{available_models[0]}' in your .env configuration.")
    else:
        print("⚠️ No content-generation models found for this project.")
except Exception as e:
    print(f"\n❌ Access Verification Failed: {e}")