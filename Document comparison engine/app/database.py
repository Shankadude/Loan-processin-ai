
import os

from pymongo import MongoClient
from dotenv import load_dotenv


load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError(
        "MONGODB_URI is not set in the environment variables."
    )

client = MongoClient(MONGODB_URI)

database = client["loan_processing"]

applications = database["loan_applications"]

def get_application(application_id: str) -> dict | None:
    """
    Retrieve one loan application from MongoDB.

    Parameters:
        application_id: MongoDB _id of the application.

    Returns:
        The application document as a Python dictionary,
        or None if the application does not exist.
    """

    document = applications.find_one(
        {"_id": application_id}
    )

    return document

def get_all_applications() -> list[dict]:
    """
    Retrieve all loan application documents from MongoDB.

    Returns:
        List of application documents.
    """

    return list(applications.find())
def update_comparison_result(
    application_id: str,
    comparison_result: dict
) -> None:
    """
    Store the comparison result inside the application document.
    """

    applications.update_one(
        {"_id": application_id},
        {
            "$set": {
                "comparison_status": "COMPLETED",
                "comparison_result": comparison_result
            }
        }
    )