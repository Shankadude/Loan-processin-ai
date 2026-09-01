import os

from pymongo import MongoClient
from dotenv import load_dotenv


load_dotenv()


MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError(
        "MONGODB_URI is not set in the .env file."
    )


client = MongoClient(MONGODB_URI)


db = client["loan_processing"]


def get_db():
    """
    Return the MongoDB database instance.
    """
    return db