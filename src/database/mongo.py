import motor.motor_asyncio
from src.config import settings

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
comparison_results_collection = db.get_collection("comparison_results")
step5_and_6_collection = db.get_collection("step5_and_6_evaluations")
full_pipeline_collection = db.get_collection("full_pipeline_records")