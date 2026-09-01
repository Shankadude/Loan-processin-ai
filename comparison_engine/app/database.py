import os

from pymongo import MongoClient

from dotenv import load_dotenv


load_dotenv()


# =====================================================
# MONGODB CONFIGURATION
# =====================================================

MONGODB_URI = os.getenv(
    "MONGODB_URI"
)

if not MONGODB_URI:

    raise ValueError(
        "MONGODB_URI is not set "
        "in the environment variables."
    )


client = MongoClient(
    MONGODB_URI
)

database = client[
    "loan_processing"
]

applications = database[
    "loan_applications"
]


# =====================================================
# GET ONE APPLICATION
# =====================================================

def get_application(
    application_id: str,
):

    return applications.find_one(
        {
            "_id": application_id
        }
    )


# =====================================================
# GET ALL APPLICATIONS
# =====================================================

def get_all_applications():

    return list(
        applications.find()
    )


# =====================================================
# SAVE COMPARISON RESULT
# =====================================================

def update_comparison_result(
    application_id: str,
    comparison_result: dict,
):

    result = applications.update_one(

        {
            "_id": application_id
        },

        {
            "$set": {

                "comparison_status": (
                    "COMPLETED"
                ),

                "comparison_result": (
                    comparison_result
                ),
            }
        },
    )

    return result