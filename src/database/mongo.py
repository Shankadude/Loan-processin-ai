import motor.motor_asyncio
from src.config import settings

# This is mongodb file to run on both local and Atlas

is_atlas = "mongodb+srv" in settings.MONGO_DETAILS or "ssl=true" in settings.MONGO_DETAILS.lower()

client_kwargs = {"serverSelectionTimeoutMS": 5000}
if is_atlas:
    client_kwargs["tls"] = True
    client_kwargs["tlsAllowInvalidCertificates"] = True

client = motor.motor_asyncio.AsyncIOMotorClient(
    settings.MONGO_DETAILS,
    **client_kwargs
)

db = client.loan_processing
applications_collection = db.get_collection("loan_applications")
verified_collection = db.get_collection("verified_documents")